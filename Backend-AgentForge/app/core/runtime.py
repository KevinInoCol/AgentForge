"""Orquesta UN turno de conversación end-to-end. Es el corazón del runtime.

Lo invoca el callback del debounce (con el texto ya concatenado). Debe ser corto:
solo ensambla piezas.
"""
import logging

from app.chat_history import append_message, get_or_create_conversation, load_history
from app.chat_history.supabase_store import update_conversation
from app.core.agent_factory import TenantAgentConfig, build_agent, resolve_openai_key
from app.core.transcription import transcribe_audio
from app.db.queries import (
    agent_has_knowledge,
    get_active_agent_for_location,
    get_agent,
    get_location_by_ghl_id,
    get_stage_route,
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
    contact_name: str | None = None,
    pipeline_id: str | None = None,
    stage_id: str | None = None,
    opportunity_id: str | None = None,
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

    # 2. Elegir agente: por etapa del embudo (si aplica) o el agente publicado.
    agent_row = None
    if pipeline_id and stage_id:
        route = await get_stage_route(location["id"], pipeline_id, stage_id)
        if route and route.get("agent_id"):
            cand = await get_agent(route["agent_id"])
            if cand and cand.get("published") and cand.get("enabled"):
                agent_row = cand
                logger.warning("[turn] 🎯 enrutado por etapa %s → agente '%s'", stage_id, cand["name"])
    if not agent_row:
        agent_row = await get_active_agent_for_location(location["id"])
    if not agent_row:
        logger.warning("[turn] ❌ Sin agente PUBLICADO en el workspace %s (publícalo)", location["id"])
        return

    # 3. Conversación + guarda de handoff humano
    conversation = await get_or_create_conversation(
        location["id"], contact_id, contact_name=contact_name, agent_id=agent_row["id"]
    )
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

    # 7. Reloj de seguimiento: el contacto acaba de escribir y la IA respondió.
    #    Anclamos el reloj en ESTA respuesta y reseteamos el contador (si el
    #    contacto vuelve a escribir, este ciclo se reinicia al próximo turno).
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()
    await update_conversation(
        conversation["id"],
        {
            "last_inbound_at": now_iso,
            "followup_anchor_at": now_iso,
            "followups_sent": 0,
            "channel": channel,
        },
    )
    # TODO: record_usage(location_id, tokens) para billing
