"""Flujos OAuth 2.0.

  - GHL Marketplace App (pendiente / escala).
  - Google (Calendar, etc.): callback que canjea el `code` y guarda la conexión
    del workspace. El workspace viene en el `state` firmado (ver api/connections.py),
    porque Google redirige aquí SIN token de sesión.
"""
import logging

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.crypto import encrypt_json, verify_state
from app.db.queries import upsert_connection
from app.integrations.google.oauth import exchange_code, get_account_email

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/install")
def install_redirect():
    """Devuelve la URL de autorización de GHL para iniciar el OAuth."""
    # TODO: construir URL con client_id, redirect_uri y scopes
    return {"todo": "redirigir al consent screen de GHL"}


@router.get("/callback")
async def oauth_callback(code: str, locationId: str | None = None):
    """GHL redirige aquí tras autorizar. Intercambia `code` por tokens."""
    # TODO: POST a la API de token de GHL, guardar tokens en `locations`
    return {"todo": "guardar tokens del tenant", "code": bool(code)}


def _redirect_credentials(status: str) -> RedirectResponse:
    """Vuelve al panel (pestaña Credenciales) con el resultado de la conexión."""
    return RedirectResponse(f"{settings.frontend_url}/credentials?google={status}")


@router.get("/google/callback")
async def google_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    """Google redirige aquí tras el consent. Canjea el code y guarda la conexión.

    No hay sesión: la confianza viene del `state` firmado (lleva el workspace_id).
    """
    if error or not code or not state:
        logger.warning("[google-oauth] callback sin code/state (error=%s)", error)
        return _redirect_credentials("error")
    try:
        payload = verify_state(state)
        workspace_id = payload["workspace_id"]
    except Exception:  # noqa: BLE001
        logger.warning("[google-oauth] state inválido o expirado")
        return _redirect_credentials("error")

    try:
        creds = await exchange_code(code)
        if not creds.get("refresh_token"):
            # Sin refresh_token no podríamos renovar el acceso (pasa si el usuario
            # ya había autorizado antes sin prompt=consent). Lo tratamos como error.
            logger.warning("[google-oauth] Google no devolvió refresh_token")
            return _redirect_credentials("error")
        email = await get_account_email(creds["access_token"])
        await upsert_connection(
            {
                "location_id": workspace_id,
                "provider": "google_calendar",
                "status": "active",
                "account_email": email,
                "credentials": encrypt_json(creds),
                "config": {"calendar_id": "primary"},
                "scopes": creds.get("scope", ""),
            }
        )
        logger.warning("[google-oauth] ✅ conexión guardada (ws=%s, %s)", workspace_id, email)
    except Exception:  # noqa: BLE001
        logger.exception("[google-oauth] falló el canje/guardado")
        return _redirect_credentials("error")

    return _redirect_credentials("connected")
