"""CRUD de agentes — lo que consume el frontend.

Los agentes pertenecen a un `workspace_id` (id interno del tenant), que a su vez
pertenece a un usuario. Todos los endpoints requieren auth y verifican que el
usuario sea dueño del workspace/agente.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import get_current_user_id, require_owned_agent, require_owned_workspace
from app.core.agent_factory import TenantAgentConfig, build_agent, resolve_openai_key
from app.core.agent_generator import generate_agent
from app.db.queries import (
    create_agent_row,
    delete_agent_row,
    list_agents_for_location,
    update_agent_row,
)

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
    agent = build_agent(cfg, api_key=api_key)
    result = await agent.ainvoke({"messages": body.messages})
    return {"reply": result["messages"][-1].content}


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
