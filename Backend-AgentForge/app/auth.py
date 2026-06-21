"""Autenticación vía Supabase Auth.

El frontend inicia sesión con Supabase y envía el access token (JWT) en el header
Authorization. Aquí lo verificamos contra Supabase para obtener el user id, y
validamos que el usuario sea dueño del workspace/agente que toca.
"""
import asyncio

from fastapi import Header, HTTPException

from app.db.queries import get_agent, get_location_by_id
from app.db.supabase import get_supabase


async def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    """Dependencia FastAPI: devuelve el id del usuario autenticado o lanza 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "No autenticado")
    token = authorization.split(" ", 1)[1].strip()
    try:
        res = await asyncio.to_thread(lambda: get_supabase().auth.get_user(token))
    except Exception:  # noqa: BLE001
        raise HTTPException(401, "Token inválido o expirado")
    if not res or not getattr(res, "user", None):
        raise HTTPException(401, "Token inválido")
    return res.user.id


async def require_owned_workspace(workspace_id: str, user_id: str) -> dict:
    ws = await get_location_by_id(workspace_id)
    if not ws:
        raise HTTPException(404, "Workspace no encontrado")
    if ws.get("owner_user_id") != user_id:
        raise HTTPException(403, "No tienes acceso a este workspace")
    return ws


async def require_owned_agent(agent_id: str, user_id: str) -> dict:
    agent = await get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agente no encontrado")
    ws = await get_location_by_id(agent["location_id"])
    if not ws or ws.get("owner_user_id") != user_id:
        raise HTTPException(403, "No tienes acceso a este agente")
    return agent
