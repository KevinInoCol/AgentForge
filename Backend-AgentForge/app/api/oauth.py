"""Flujo OAuth 2.0 de la Marketplace App de GoHighLevel.

Cuando una sub-cuenta instala la app, GHL redirige aquí con un `code`.
Se intercambia por access/refresh token y se guarda en la tabla `locations`.
"""
from fastapi import APIRouter

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
