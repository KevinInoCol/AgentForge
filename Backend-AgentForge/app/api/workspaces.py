"""Workspaces (tenant) — uno por usuario autenticado (Supabase Auth).

El workspace se obtiene/crea con GET /me a partir del usuario del token.
La conexión con GHL (LocationID + PIT) se hace al Publicar (go-live).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user_id, require_owned_workspace
from app.chat_history.supabase_store import update_conversation
from app.core.agent_factory import resolve_openai_key
from app.core.analysis import analyze_conversation
from app.db.queries import (
    get_agent,
    get_conversation,
    get_location_by_owner,
    insert_workspace,
    list_stage_routes,
    replace_stage_routes,
    update_location_row,
    upsert_pipeline,
    workspace_contacts,
    workspace_unresponded,
)
from app.integrations.ghl.client import GHLClient

logger = logging.getLogger(__name__)
router = APIRouter()


class OpenAISettingsIn(BaseModel):
    openai_api_key: str | None = None
    default_model: str | None = None


class GHLConnectIn(BaseModel):
    ghl_location_id: str
    private_integration_token: str


def _status(ws: dict) -> dict:
    return {
        "id": ws["id"],
        "name": ws.get("name"),
        "has_openai_key": bool(ws.get("openai_api_key")),
        "default_model": ws.get("default_model") or "gpt-4.1",
        "has_pit": bool(ws.get("private_integration_token")),
        "ghl_location_id": ws.get("ghl_location_id"),
        "ghl_connected": bool(ws.get("ghl_location_id") and ws.get("private_integration_token")),
    }


@router.get("/me")
async def my_workspace(user_id: str = Depends(get_current_user_id)):
    """Devuelve el workspace del usuario; lo crea si aún no tiene."""
    ws = await get_location_by_owner(user_id)
    if not ws:
        ws = await insert_workspace(owner_user_id=user_id)
    return _status(ws)


@router.post("/ghl/test")
async def test_ghl(body: GHLConnectIn, user_id: str = Depends(get_current_user_id)):
    """Valida el PIT contra GHL antes de conectar."""
    client = GHLClient(body.private_integration_token)
    try:
        await client.verify_location(body.ghl_location_id)
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": str(e)}
    finally:
        await client.aclose()


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    ws = await require_owned_workspace(workspace_id, user_id)
    return _status(ws)


@router.get("/{workspace_id}/unresponded")
async def get_unresponded(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    """Contactos que no respondieron, con su análisis (para la pestaña Análisis)."""
    await require_owned_workspace(workspace_id, user_id)
    return {"contacts": await workspace_unresponded(workspace_id)}


@router.post("/{workspace_id}/conversations/{conversation_id}/analyze")
async def analyze_one(workspace_id: str, conversation_id: str, user_id: str = Depends(get_current_user_id)):
    """Analiza bajo demanda por qué un contacto no avanzó (consume tokens)."""
    ws = await require_owned_workspace(workspace_id, user_id)
    convo = await get_conversation(conversation_id)
    if not convo or convo.get("location_id") != workspace_id:
        raise HTTPException(404, "Conversación no encontrada")
    api_key = resolve_openai_key(ws)
    if not api_key:
        raise HTTPException(400, "Configura tu API key de OpenAI en 🧠 Credenciales OpenAI.")
    agent = await get_agent(convo["agent_id"]) if convo.get("agent_id") else None
    persona = agent["system_prompt"] if agent else ""
    model = agent["model"] if agent else "gpt-4.1"

    analysis = await analyze_conversation(conversation_id, persona, model, api_key)
    from datetime import datetime, timezone

    await update_conversation(conversation_id, {
        "analysis_reason": analysis.get("reason"),
        "analysis_objection": analysis.get("objection"),
        "analysis_recommendation": analysis.get("recommendation"),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    })
    return analysis


@router.get("/{workspace_id}/contacts")
async def get_contacts(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    """Contactos con los que la IA ha conversado + métricas de interacción."""
    await require_owned_workspace(workspace_id, user_id)
    contacts = await workspace_contacts(workspace_id)
    total_interactions = sum(c.get("interactions") or 0 for c in contacts)
    return {
        "contacts": contacts,
        "total_contacts": len(contacts),
        "total_interactions": total_interactions,
    }


class RoutesIn(BaseModel):
    pipeline_id: str
    routes: list[dict]  # [{stage_id, agent_id}]


@router.get("/{workspace_id}/pipelines")
async def get_pipelines(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    """Trae los pipelines/etapas desde GHL y los cachea. Requiere GHL conectado."""
    ws = await require_owned_workspace(workspace_id, user_id)
    if not ws.get("ghl_location_id") or not ws.get("private_integration_token"):
        raise HTTPException(400, "Conecta HighLevel (Credenciales) para cargar tus embudos.")
    client = GHLClient(ws["private_integration_token"])
    try:
        data = await client.list_pipelines(ws["ghl_location_id"])
    finally:
        await client.aclose()

    pipelines = []
    for p in data.get("pipelines", []):
        stages = [
            {"id": s.get("id"), "name": s.get("name"), "position": s.get("position", 0)}
            for s in p.get("stages", [])
        ]
        await upsert_pipeline(workspace_id, p["id"], p.get("name"), stages)
        pipelines.append({"id": p["id"], "name": p.get("name"), "stages": stages})
    return {"pipelines": pipelines}


@router.get("/{workspace_id}/routes")
async def get_routes(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    await require_owned_workspace(workspace_id, user_id)
    return {"routes": await list_stage_routes(workspace_id)}


@router.post("/{workspace_id}/routes")
async def save_routes(workspace_id: str, body: RoutesIn, user_id: str = Depends(get_current_user_id)):
    await require_owned_workspace(workspace_id, user_id)
    await replace_stage_routes(workspace_id, body.pipeline_id, body.routes)
    return {"ok": True, "saved": len([r for r in body.routes if r.get("agent_id")])}


@router.post("/{workspace_id}/openai")
async def save_openai(workspace_id: str, body: OpenAISettingsIn, user_id: str = Depends(get_current_user_id)):
    await require_owned_workspace(workspace_id, user_id)
    values: dict = {}
    if body.openai_api_key:
        values["openai_api_key"] = body.openai_api_key
    if body.default_model:
        values["default_model"] = body.default_model
    ws = await update_location_row(workspace_id, values) if values else await require_owned_workspace(workspace_id, user_id)
    return _status(ws)


@router.post("/{workspace_id}/ghl")
async def connect_ghl(workspace_id: str, body: GHLConnectIn, user_id: str = Depends(get_current_user_id)):
    """Conecta la sub-cuenta de GHL al workspace (paso de go-live)."""
    await require_owned_workspace(workspace_id, user_id)
    ws = await update_location_row(
        workspace_id,
        {
            "ghl_location_id": body.ghl_location_id,
            "private_integration_token": body.private_integration_token,
        },
    )
    return _status(ws)
