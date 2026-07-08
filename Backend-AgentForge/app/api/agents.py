"""CRUD de agentes — lo que consume el frontend.

Los agentes pertenecen a un `workspace_id` (id interno del tenant), que a su vez
pertenece a un usuario. Todos los endpoints requieren auth y verifican que el
usuario sea dueño del workspace/agente.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.RAG.rag import ingest_document
from app.auth import get_current_user_id, require_owned_agent, require_owned_workspace
from app.core.agent_factory import TenantAgentConfig, build_agent, resolve_openai_key
from app.core.agent_generator import generate_agent
from app.db.queries import (
    create_agent_row,
    delete_agent_row,
    delete_document,
    get_document,
    list_agents_for_location,
    list_documents,
    update_agent_row,
)
from app.tools.catalog import build_tools_for_agent

router = APIRouter()


class AgentIn(BaseModel):
    workspace_id: str
    name: str
    system_prompt: str
    model: str = "gpt-4.1"
    temperature: float = 0.0
    enabled: bool = True
    tools: list[str] = []


class AgentUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    enabled: bool | None = None
    published: bool | None = None
    tools: list[str] | None = None
    followups_enabled: bool | None = None
    followup_messages: list[str] | None = None
    followup_mode: str | None = None  # 'fixed' | 'ai'


class GenerateIn(BaseModel):
    name: str = ""
    description: str
    model: str = "gpt-4.1"
    workspace_id: str | None = None  # para usar la OpenAI key del workspace


@router.post("/generate")
async def generate(body: GenerateIn, user_id: str = Depends(get_current_user_id)):
    """Genera un borrador (name + system_prompt) con IA. NO lo guarda."""
    ws = await require_owned_workspace(body.workspace_id, user_id) if body.workspace_id else None
    api_key = resolve_openai_key(ws)
    if not api_key:
        raise HTTPException(400, "Configura tu API key de OpenAI en 🧠 Credenciales OpenAI antes de generar.")
    return await generate_agent(body.name, body.description, body.model, api_key=api_key)


class ChatIn(BaseModel):
    messages: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


@router.post("/{agent_id}/chat")
async def chat(agent_id: str, body: ChatIn, user_id: str = Depends(get_current_user_id)):
    """Chat Lab: prueba el agente en vivo. Efímero — NO persiste la conversación."""
    agent_row = await require_owned_agent(agent_id, user_id)
    ws = await require_owned_workspace(agent_row["location_id"], user_id)
    api_key = resolve_openai_key(ws)
    if not api_key:
        raise HTTPException(400, "Configura tu API key de OpenAI en 🧠 Credenciales OpenAI antes de probar el agente.")
    cfg = TenantAgentConfig.from_row(agent_row)
    tools = await build_tools_for_agent(agent_row, ws, api_key)
    agent = build_agent(cfg, api_key=api_key, tools=tools)
    result = await agent.ainvoke({"messages": body.messages})
    return {"reply": result["messages"][-1].content}


# ── Base de conocimiento (RAG) ───────────────────────────────────────

@router.post("/{agent_id}/knowledge")
async def upload_knowledge(
    agent_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """Sube un documento (PDF/TXT) a la base de conocimiento del agente."""
    agent_row = await require_owned_agent(agent_id, user_id)
    ws = await require_owned_workspace(agent_row["location_id"], user_id)
    api_key = resolve_openai_key(ws)
    if not api_key:
        raise HTTPException(400, "Configura tu API key de OpenAI en 🧠 Credenciales OpenAI antes de subir documentos.")
    name = (file.filename or "").lower()
    if not (name.endswith(".pdf") or name.endswith(".txt")):
        raise HTTPException(400, "Solo se admiten archivos .pdf o .txt")
    data = await file.read()
    chunks = await ingest_document(agent_id, file.filename, data, api_key)
    if chunks == 0:
        raise HTTPException(400, "No se pudo extraer texto del archivo (¿PDF escaneado/sin texto?).")
    return {"filename": file.filename, "chunks": chunks}


@router.get("/{agent_id}/knowledge")
async def list_knowledge(agent_id: str, user_id: str = Depends(get_current_user_id)):
    await require_owned_agent(agent_id, user_id)
    return {"documents": await list_documents(agent_id)}


@router.delete("/{agent_id}/knowledge/{document_id}")
async def delete_knowledge(agent_id: str, document_id: str, user_id: str = Depends(get_current_user_id)):
    await require_owned_agent(agent_id, user_id)
    doc = await get_document(document_id)
    if not doc or doc["agent_id"] != agent_id:
        raise HTTPException(404, "Documento no encontrado")
    await delete_document(document_id)
    return {"deleted": document_id}


@router.get("")
async def list_agents(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    """Lista los agentes del workspace del usuario."""
    await require_owned_workspace(workspace_id, user_id)
    agents = await list_agents_for_location(workspace_id)
    return {"agents": agents}


@router.get("/{agent_id}")
async def get_one(agent_id: str, user_id: str = Depends(get_current_user_id)):
    return await require_owned_agent(agent_id, user_id)


@router.post("")
async def create_agent(cfg: AgentIn, user_id: str = Depends(get_current_user_id)):
    await require_owned_workspace(cfg.workspace_id, user_id)
    values = cfg.model_dump(exclude={"workspace_id"})
    values["location_id"] = cfg.workspace_id
    return await create_agent_row(values)


@router.put("/{agent_id}")
async def update_agent(agent_id: str, cfg: AgentUpdate, user_id: str = Depends(get_current_user_id)):
    await require_owned_agent(agent_id, user_id)
    values = cfg.model_dump(exclude_none=True)
    return await update_agent_row(agent_id, values)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, user_id: str = Depends(get_current_user_id)):
    await require_owned_agent(agent_id, user_id)
    await delete_agent_row(agent_id)
    return {"deleted": agent_id}
