"""Orquesta UN turno de conversación end-to-end. Es el corazón del runtime.

Lo invoca el callback del debounce (con el texto ya concatenado). Debe ser corto:
solo ensambla piezas.
"""
import logging

from app.chat_history import append_message, get_or_create_conversation, load_history
from app.core.agent_factory import TenantAgentConfig, build_agent, resolve_openai_key
from app.core.transcription import transcribe_audio
from app.db.queries import (
    agent_has_knowledge,
    get_active_agent_for_location,
    get_location_by_ghl_id,
)
from app.integrations.ghl.client import GHLClient
from app.tools.knowledge import get_knowledge_tool

logger = logging.getLogger(__name__)


async def process_turn(
    ghl_location_id: str,
    contact_id: str,
    text: str,
    channel: str = "SMS",
    audio_url: str | None = None,
) -> None:
    """Procesa el mensaje (texto o audio) y responde por GHL."""
    logger.warning(
        "[turn] loc=%s contact=%s canal=%s texto=%r audio=%s",
        ghl_location_id, contact_id, channel, text, bool(audio_url),
    )

    # 1. Tenant + token
    location = await get_location_by_ghl_id(ghl_location_id)
    if not location:
        logger.warning("[turn] ❌ Sub-cuenta desconocida: %s (conéctala en Credenciales HighLevel)", ghl_location_id)
        return

    # 2. Agente activo de la sub-cuenta
    agent_row = await get_active_agent_for_location(location["id"])
    if not agent_row:
        logger.warning("[turn] ❌ Sin agente PUBLICADO en el workspace %s (publícalo)", location["id"])
        return

    # 3. Conversación + guarda de handoff humano
    conversation = await get_or_create_conversation(location["id"], contact_id)
    if conversation.get("human_handoff"):
        logger.warning("[turn] ⏸ Handoff humano activo; IA en pausa (%s)", contact_id)
        return

    if not location.get("private_integration_token"):
        logger.warning("[turn] ❌ Sin PIT en el workspace; no se puede responder a GHL")
        return

    api_key = resolve_openai_key(location)
    if not api_key:
        logger.warning("[turn] ❌ Sin OpenAI key en el workspace (ponla en Credenciales OpenAI)")
        return

    # 3.5. Si vino un audio (sin texto), transcribirlo con Whisper.
    if not text and audio_url:
        try:
            text = await transcribe_audio(audio_url, api_key)
        except Exception:  # noqa: BLE001
            logger.exception("[turn] ❌ Falló la transcripción del audio")
            return
    if not text:
        logger.warning("[turn] ❌ Sin texto que procesar (¿audio vacío?)")
        return

    # 4. Historial + agente (con la OpenAI key de la sub-cuenta)
    history = await load_history(conversation["id"])
    cfg = TenantAgentConfig.from_row(agent_row)
    tools = []
    if await agent_has_knowledge(cfg.agent_id):
        tools.append(get_knowledge_tool(cfg.agent_id, api_key))
    agent = build_agent(cfg, api_key=api_key, tools=tools)

    messages = history + [{"role": "user", "content": text}]
    result = await agent.ainvoke({"messages": messages})
    reply = result["messages"][-1].content
    logger.warning("[turn] 🤖 respuesta generada: %r", reply[:120])

    # 5. Enviar respuesta por el mismo canal
    client = GHLClient(location["private_integration_token"])
    try:
        await client.send_message(contact_id, reply, channel=channel)
        logger.warning("[turn] ✅ enviado a GHL (contact=%s, canal=%s)", contact_id, channel)
    finally:
        await client.aclose()

    # 6. Persistir (alimenta transcripts + metering)
    await append_message(conversation["id"], "user", text)
    await append_message(conversation["id"], "assistant", reply)
    # TODO: record_usage(location_id, tokens) para billing
