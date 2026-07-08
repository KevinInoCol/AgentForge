"""OAuth 2.0 con Google (a nivel plataforma).

Una sola app de Google Cloud (client_id/secret en .env) sirve a todos los tenants.
Cada tenant conecta SU cuenta: lo mandamos al consent screen, Google nos devuelve
un `code`, lo canjeamos por tokens (guardamos el refresh_token, que no expira) y
refrescamos el access_token cuando haga falta.

Docs: https://developers.google.com/identity/protocols/oauth2/web-server
"""
import time
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"

# Scopes por proveedor. Calendar: leer/escribir eventos + email para mostrar la cuenta.
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]


def build_auth_url(state: str, scopes: list[str]) -> str:
    """URL del consent screen. `state` viaja de ida y vuelta (lo firmamos)."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",   # para recibir refresh_token
        "prompt": "consent",         # fuerza refresh_token también en reconexiones
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Canjea el `code` por tokens. Devuelve el dict de credenciales a cifrar."""
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            TOKEN_URI,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tok = resp.json()
    return {
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token", ""),
        "expires_at": time.time() + tok.get("expires_in", 3600),
        "scope": tok.get("scope", ""),
    }


async def refresh_access_token(creds: dict) -> dict:
    """Renueva el access_token usando el refresh_token. Devuelve creds actualizadas."""
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            TOKEN_URI,
            data={
                "refresh_token": creds["refresh_token"],
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        tok = resp.json()
    creds = {**creds, "access_token": tok["access_token"], "expires_at": time.time() + tok.get("expires_in", 3600)}
    return creds


async def get_account_email(access_token: str) -> str | None:
    """Email de la cuenta conectada (para mostrar 'Conectado como ...')."""
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(USERINFO_URI, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            return None
        return resp.json().get("email")


async def valid_access_token(creds: dict) -> tuple[str, dict]:
    """Devuelve un access_token vigente (refrescando si expiró) y las creds usadas.

    El caller debe re-guardar las creds si cambiaron (compara por identidad/expires_at).
    """
    if creds.get("expires_at", 0) - 60 > time.time():
        return creds["access_token"], creds
    refreshed = await refresh_access_token(creds)
    return refreshed["access_token"], refreshed
