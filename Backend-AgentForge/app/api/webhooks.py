"""Webhook de GHL para mensajes entrantes.

El Workflow de GHL (trigger "Customer Replied" → acción Webhook) envía nuestros
campos anidados dentro de `customData`, y el `messageType` viene como código
NUMÉRICO (ej. 11 = Facebook). Aquí los extraemos y normalizamos el canal.
"""
import logging

from fastapi import APIRouter, Request

from app.buffer.debounce import enqueue_message
from app.core.runtime import process_turn

logger = logging.getLogger(__name__)
router = APIRouter()

# GHL manda el tipo de mensaje como número en el webhook; la API de ENVÍO espera
# un string de canal. Mapeo de los códigos observados (se amplía con los logs).
_CHANNEL_MAP = {
    "1": "SMS",
    "3": "Email",
    "11": "FB",   # Facebook Messenger (confirmado en prueba 2026-06-21)
    "12": "IG",   # Instagram (tentativo — confirmar en logs)
    # strings que ya vienen listos:
    "SMS": "SMS", "Email": "Email", "WhatsApp": "WhatsApp", "FB": "FB",
    "IG": "IG", "Live_Chat": "Live_Chat",
}


def _normalize_channel(raw) -> str:
    if raw is None:
        return "SMS"
    key = str(raw)
    mapped = _CHANNEL_MAP.get(key)
    if mapped:
        return mapped
    logger.warning("messageType desconocido: %r — usando tal cual", raw)
    return key


@router.post("/ghl/inbound")
async def ghl_inbound(request: Request):
    payload = await request.json()

    # GHL anida los campos personalizados del workflow dentro de `customData`.
    data = payload.get("customData") or payload

    location_id = data.get("locationId")
    contact_id = data.get("contactId")
    text = data.get("message") or data.get("body")
    channel = _normalize_channel(data.get("messageType") or data.get("type"))

    if not (location_id and contact_id and text):
        if location_id and contact_id and not text:
            # Sin texto = posible audio/adjunto. Logueamos el payload completo
            # para descubrir dónde viene la URL del audio (diagnóstico temporal).
            logger.warning("[audio?] Mensaje sin texto. PAYLOAD COMPLETO=%s", payload)
        else:
            logger.warning("Payload incompleto. customData=%s", data)
        return {"received": False, "reason": "missing fields"}

    async def _process(combined: str) -> None:
        try:
            await process_turn(location_id, contact_id, combined, channel=channel)
        except Exception:  # noqa: BLE001 — no romper el buffer por un fallo de turno
            logger.exception("Error procesando turno (%s/%s)", location_id, contact_id)

    buffer_id = f"{location_id}:{contact_id}"
    await enqueue_message(buffer_id, text, _process)

    return {"received": True}
