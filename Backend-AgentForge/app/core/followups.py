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

from app.chat_history.supabase_store import append_message, load_history, update_conversation
from app.config import settings
from app.core.analysis import generate_followup_with_analysis
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
        if idx >= len(THRESHOLDS_HOURS):
            continue
        anchor = r.get("followup_anchor_at")
        if not anchor or _hours_since(anchor) < THRESHOLDS_HOURS[idx]:
            continue  # aún no toca este seguimiento

        cid = r["conversation_id"]
        mode = r.get("followup_mode") or "fixed"
        analysis = None  # se llena en modo IA → se guarda para el tab de Análisis

        # Determinar el mensaje según el modo.
        try:
            if mode == "ai":
                api_key = r.get("openai_api_key") or settings.openai_api_key
                if not api_key:
                    logger.warning("[followup] modo IA sin OpenAI key; salto (conv=%s)", cid)
                    continue
                history = await load_history(cid, limit=30)
                draft = await generate_followup_with_analysis(
                    history, r.get("agent_system_prompt") or "", r.get("agent_model") or "gpt-4.1", api_key, idx
                )
                msg = (draft.get("message") or "").strip()
                analysis = draft  # incluye reason/objection/recommendation
            else:
                messages = r.get("followup_messages") or []
                raw = messages[idx] if idx < len(messages) else ""
                msg = (raw or "").strip()
        except Exception:  # noqa: BLE001
            logger.exception("[followup] error generando mensaje (conv=%s)", cid)
            continue

        if not msg:
            # nada que enviar en este escalón → avanzar el contador
            await update_conversation(cid, {"followups_sent": idx + 1})
            continue

        client = GHLClient(r["pit"])
        try:
            await client.send_message(r["ghl_contact_id"], msg, channel=r.get("channel") or "SMS")
            update_vals = {"followups_sent": idx + 1}
            if analysis:
                update_vals.update({
                    "analysis_reason": analysis.get("reason"),
                    "analysis_objection": analysis.get("objection"),
                    "analysis_recommendation": analysis.get("recommendation"),
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                })
            await update_conversation(cid, update_vals)
            await append_message(cid, "assistant", msg)
            logger.warning("[followup] ✅ seguimiento #%d (%s) enviado a %s", idx + 1, mode, r["ghl_contact_id"])
        except Exception:  # noqa: BLE001
            logger.exception("[followup] error enviando seguimiento a %s", r.get("ghl_contact_id"))
        finally:
            await client.aclose()
