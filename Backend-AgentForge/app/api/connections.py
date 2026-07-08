"""Conexiones a servicios externos (tools con OAuth) — lo que consume el frontend.

Flujo OAuth (Google Calendar):
  1. Frontend (autenticado) llama a /google/start?workspace_id=... → devuelve la URL
     del consent de Google, con un `state` firmado que lleva el workspace_id.
  2. El usuario autoriza en Google; Google redirige a /oauth/google/callback (ver
     app/api/oauth.py) SIN token de sesión: por eso confiamos en el `state` firmado.
  3. El callback canjea el code, cifra los tokens y guarda la conexión.

El catálogo de tools se sirve aquí para que la UI del agente pinte los toggles.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user_id, require_owned_workspace
from app.core.crypto import sign_state
from app.db.queries import (
    delete_connection,
    get_connection_by_id,
    list_connections,
)
from app.integrations.google.oauth import CALENDAR_SCOPES, build_auth_url
from app.tools.catalog import catalog_public

router = APIRouter()


@router.get("/catalog")
async def tools_catalog(user_id: str = Depends(get_current_user_id)):
    """Catálogo de tools habilitables (para pintar los toggles del agente)."""
    return {"tools": catalog_public()}


@router.get("")
async def get_connections(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    """Conexiones del workspace (sin credenciales)."""
    await require_owned_workspace(workspace_id, user_id)
    return {"connections": await list_connections(workspace_id)}


@router.get("/google/start")
async def google_start(workspace_id: str, user_id: str = Depends(get_current_user_id)):
    """Devuelve la URL del consent de Google Calendar para este workspace."""
    await require_owned_workspace(workspace_id, user_id)
    state = sign_state({"workspace_id": workspace_id, "provider": "google_calendar"})
    return {"url": build_auth_url(state, CALENDAR_SCOPES)}


@router.delete("/{connection_id}")
async def remove_connection(connection_id: str, user_id: str = Depends(get_current_user_id)):
    """Desconecta un servicio (borra la conexión y sus credenciales)."""
    conn = await get_connection_by_id(connection_id)
    if not conn:
        raise HTTPException(404, "Conexión no encontrada")
    await require_owned_workspace(conn["location_id"], user_id)
    await delete_connection(connection_id)
    return {"ok": True}
