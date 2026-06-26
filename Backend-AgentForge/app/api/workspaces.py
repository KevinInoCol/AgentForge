"""Workspaces (tenant) — uno por usuario autenticado (Supabase Auth).

El workspace se obtiene/crea con GET /me a partir del usuario del token.
La conexión con GHL (LocationID + PIT) se hace al Publicar (go-live).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user_id, require_owned_workspace
from app.db.queries import (
    get_location_by_owner,
    insert_workspace,
    update_location_row,
    workspace_contacts,
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
