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
    text = data.get("message") or data.get("body") or ""
    audio_url = data.get("multimedia") or None  # URL del adjunto (nota de voz)
    channel = _normalize_channel(data.get("messageType") or data.get("type"))
    # Nombre del contacto (viene en la raíz del payload de GHL, no en customData).
    contact_name = (
        payload.get("full_name")
        or " ".join(filter(None, [payload.get("first_name"), payload.get("last_name")]))
        or None
    )

    # Necesitamos tenant + contacto, y al menos texto O audio.
    if not location_id or not contact_id or (not text and not audio_url):
        logger.warning(
            "Payload sin contenido procesable (loc=%s contact=%s text=%s audio=%s)",
            location_id, contact_id, bool(text), bool(audio_url),
        )
        return {"received": False, "reason": "missing fields"}

    async def _process(combined: str) -> None:
        try:
            await process_turn(location_id, contact_id, combined, channel=channel, audio_url=audio_url, contact_name=contact_name)
        except Exception:  # noqa: BLE001 — no romper el buffer por un fallo de turno
            logger.exception("Error procesando turno (%s/%s)", location_id, contact_id)

    buffer_id = f"{location_id}:{contact_id}"
    await enqueue_message(buffer_id, text, _process)  # audio: text="" → se transcribe en process_turn

    return {"received": True}
