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

from openai import AsyncOpenAI

from app.chat_history.supabase_store import append_message, load_history, update_conversation
from app.config import settings
from app.db.queries import due_followups
from app.integrations.ghl.client import GHLClient

logger = logging.getLogger(__name__)

THRESHOLDS_HOURS = [4, 8, 12]


async def _generate_ai_followup(
    conversation_id: str, persona_prompt: str, model: str, api_key: str, attempt: int
) -> str:
    """Agente de Seguimiento: analiza la conversación y redacta un mensaje persuasivo."""
    history = await load_history(conversation_id, limit=30)
    system = (
        "Eres un Agente de Seguimiento experto en recuperar ventas. Analiza la conversación: "
        "identifica por qué el contacto no avanzó o no compró y qué duda/objeción quedó. "
        "Escribe UN solo mensaje breve (1-3 frases), cálido, humano y persuasivo para retomarlo "
        "y cerrar la venta. No te repitas respecto a seguimientos anteriores. Habla como el mismo "
        "asistente del negocio.\n\nContexto del asistente:\n" + (persona_prompt or "")
    )
    messages = (
        [{"role": "system", "content": system}]
        + history
        + [{
            "role": "user",
            "content": f"(Pasaron horas sin respuesta. Es el seguimiento #{attempt + 1}. "
                       "Escribe SOLO el mensaje a enviar, sin comillas ni explicaciones.)",
        }]
    )
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(model=model, messages=messages, temperature=0.7)
    return (resp.choices[0].message.content or "").strip()


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

        # Determinar el mensaje según el modo.
        try:
            if mode == "ai":
                api_key = r.get("openai_api_key") or settings.openai_api_key
                if not api_key:
                    logger.warning("[followup] modo IA sin OpenAI key; salto (conv=%s)", cid)
                    continue
                msg = await _generate_ai_followup(
                    cid, r.get("agent_system_prompt") or "", r.get("agent_model") or "gpt-4.1", api_key, idx
                )
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
            await update_conversation(cid, {"followups_sent": idx + 1})
            await append_message(cid, "assistant", msg)
            logger.warning("[followup] ✅ seguimiento #%d (%s) enviado a %s", idx + 1, mode, r["ghl_contact_id"])
        except Exception:  # noqa: BLE001
            logger.exception("[followup] error enviando seguimiento a %s", r.get("ghl_contact_id"))
        finally:
            await client.aclose()
