"""Webhook de GHL para mensajes entrantes.

REGLA DE ORO: responder en milisegundos. Aquí NO se llama al LLM.
Se valida, se identifica el tenant y se empuja al buffer (debounce). El
procesamiento real (LLM + envío) ocurre async cuando el usuario deja de escribir.

MVP: el webhook lo dispara un Workflow de GHL (trigger "Customer Replied" →
acción Webhook) usando PIT. Payload esperado (configurable en el Workflow):
  { "locationId", "contactId", "message", "messageType" }
"""
import logging

from fastapi import APIRouter, Request

from app.buffer.debounce import enqueue_message
from app.core.runtime import process_turn

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ghl/inbound")
async def ghl_inbound(request: Request):
    payload = await request.json()

    # TODO: verificar firma/secreto del webhook (settings.ghl_webhook_secret)
    location_id = payload.get("locationId")
    contact_id = payload.get("contactId")
    text = payload.get("message") or payload.get("body")
    channel = payload.get("messageType") or payload.get("type") or "SMS"

    if not (location_id and contact_id and text):
        logger.warning("Payload incompleto: %s", payload)
        return {"received": False, "reason": "missing fields"}

    async def _process(combined: str) -> None:
        try:
            await process_turn(location_id, contact_id, combined, channel=channel)
        except Exception:  # noqa: BLE001 — no romper el buffer por un fallo de turno
            logger.exception("Error procesando turno (%s/%s)", location_id, contact_id)

    buffer_id = f"{location_id}:{contact_id}"
    await enqueue_message(buffer_id, text, _process)

    return {"received": True}
