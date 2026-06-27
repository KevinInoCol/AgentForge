"""Cliente de la API de GoHighLevel (v2). Toda llamada a GHL pasa por aquí.

MVP: autenticación con Private Integration Token (PIT) por sub-cuenta. El mismo
cliente sirve para OAuth en el futuro (solo cambia de dónde sale el token).
"""
import httpx

from app.config import settings
from app.db.queries import get_location_by_ghl_id

GHL_API_BASE = "https://services.leadconnectorhq.com"


class GHLClient:
    def __init__(self, token: str):
        self._http = httpx.AsyncClient(
            base_url=GHL_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Version": settings.ghl_api_version,
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    async def send_message(
        self, contact_id: str, message: str, channel: str = "SMS"
    ) -> dict:
        """Envía la respuesta del agente al contacto (Conversations API).

        `channel` ∈ {SMS, WhatsApp, FB, IG, ...}. Debe coincidir con el canal
        por el que entró el mensaje.
        """
        resp = await self._http.post(
            "/conversations/messages",
            json={"type": channel, "contactId": contact_id, "message": message},
        )
        resp.raise_for_status()
        return resp.json()

    async def verify_location(self, location_id: str) -> bool:
        """Valida que el PIT funciona consultando la sub-cuenta.

        El endpoint de Locations usa Version 2021-07-28 (distinto al de
        Conversations), así que lo sobrescribimos solo en esta llamada.
        """
        resp = await self._http.get(
            f"/locations/{location_id}", headers={"Version": "2021-07-28"}
        )
        resp.raise_for_status()
        return True

    async def list_pipelines(self, location_id: str) -> dict:
        """Pipelines y etapas de la sub-cuenta (Opportunities API, Version 2021-07-28)."""
        resp = await self._http.get(
            "/opportunities/pipelines",
            params={"locationId": location_id},
            headers={"Version": "2021-07-28"},
        )
        resp.raise_for_status()
        return resp.json()

    async def move_opportunity(self, opportunity_id: str, pipeline_id: str, stage_id: str) -> dict:
        """Mueve una oportunidad a otra etapa del embudo."""
        resp = await self._http.put(
            f"/opportunities/{opportunity_id}",
            json={"pipelineId": pipeline_id, "pipelineStageId": stage_id},
            headers={"Version": "2021-07-28"},
        )
        resp.raise_for_status()
        return resp.json()

    async def add_tag(self, contact_id: str, tag: str) -> dict:
        resp = await self._http.post(
            f"/contacts/{contact_id}/tags", json={"tags": [tag]}
        )
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._http.aclose()


async def get_client_for_location(ghl_location_id: str) -> GHLClient:
    """Carga el PIT de la sub-cuenta y devuelve un cliente listo para usar."""
    location = await get_location_by_ghl_id(ghl_location_id)
    if not location or not location.get("private_integration_token"):
        raise ValueError(f"Sub-cuenta {ghl_location_id} sin PIT configurado")
    return GHLClient(location["private_integration_token"])
