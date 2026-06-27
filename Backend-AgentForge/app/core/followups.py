"""Seguimientos / Remarketing.

Job periódico (scheduler) que envía mensajes de seguimiento a los contactos que
NO respondieron, a las 4h, 8h y 12h desde la última respuesta de la IA.

- Tiempos FIJOS: 4h, 8h, 12h (índices 0, 1, 2 de followup_messages).
- Se cancela solo: cuando el contacto responde, process_turn reancla el reloj y
  resetea followups_sent, así la conversación deja de ser candidata.
- Respeta la ventana de 24h de Meta (todos los tiempos caen dentro).
"""
import logging
from datetime import datetime, timezone

from app.chat_history.supabase_store import append_message, update_conversation
from app.db.queries import due_followups
from app.integrations.ghl.client import GHLClient

logger = logging.getLogger(__name__)

THRESHOLDS_HOURS = [4, 8, 12]


def _hours_since(iso: str) -> float:
    anchor = datetime.fromisoformat(iso)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - anchor).total_seconds() / 3600.0


async def run_followups() -> None:
    """Revisa pendientes y envía el seguimiento que corresponda (uno por conversación)."""
    try:
        rows = await due_followups()
    except Exception:  # noqa: BLE001
        logger.exception("[followup] error consultando pendientes")
        return

    for r in rows:
        idx = r.get("followups_sent", 0)
        messages = r.get("followup_messages") or []
        if idx >= len(THRESHOLDS_HOURS) or idx >= len(messages):
            continue
        anchor = r.get("followup_anchor_at")
        if not anchor:
            continue
        if _hours_since(anchor) < THRESHOLDS_HOURS[idx]:
            continue  # aún no toca este seguimiento

        msg = (messages[idx] or "").strip()
        if not msg:
            # mensaje vacío: saltar este escalón sin enviar
            await update_conversation(r["conversation_id"], {"followups_sent": idx + 1})
            continue

        client = GHLClient(r["pit"])
        try:
            await client.send_message(r["ghl_contact_id"], msg, channel=r.get("channel") or "SMS")
            await update_conversation(r["conversation_id"], {"followups_sent": idx + 1})
            await append_message(r["conversation_id"], "assistant", msg)
            logger.warning(
                "[followup] ✅ seguimiento #%d enviado (contact=%s)", idx + 1, r["ghl_contact_id"]
            )
        except Exception:  # noqa: BLE001
            logger.exception("[followup] error enviando seguimiento a %s", r.get("ghl_contact_id"))
        finally:
            await client.aclose()
