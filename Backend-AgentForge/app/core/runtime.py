"""Orquesta UN turno de conversación end-to-end. Es el corazón del runtime.

Lo invoca el callback del debounce (con el texto ya concatenado). Debe ser corto:
solo ensambla piezas.
"""
import logging

from app.chat_history import append_message, get_or_create_conversation, load_history
from app.core.agent_factory import TenantAgentConfig, build_agent, resolve_openai_key
from app.db.queries import get_active_agent_for_location, get_location_by_ghl_id
from app.integrations.ghl.client import GHLClient

logger = logging.getLogger(__name__)


async def process_turn(
    ghl_location_id: str, contact_id: str, text: str, channel: str = "SMS"
) -> None:
    """Procesa el mensaje (ya concatenado) y responde por GHL."""
    # 1. Tenant + token
    location = await get_location_by_ghl_id(ghl_location_id)
    if not location:
        logger.warning("Sub-cuenta desconocida: %s", ghl_location_id)
        return

    # 2. Agente activo de la sub-cuenta
    agent_row = await get_active_agent_for_location(location["id"])
    if not agent_row:
        logger.info("Sin agente activo para %s", ghl_location_id)
        return

    # 3. Conversación + guarda de handoff humano
    conversation = await get_or_create_conversation(location["id"], contact_id)
    if conversation.get("human_handoff"):
        logger.info("Handoff humano activo; IA en pausa (%s)", contact_id)
        return

    # 4. Historial + agente (con la OpenAI key de la sub-cuenta)
    history = await load_history(conversation["id"])
    cfg = TenantAgentConfig.from_row(agent_row)
    agent = build_agent(cfg, api_key=resolve_openai_key(location))

    messages = history + [{"role": "user", "content": text}]
    result = await agent.ainvoke({"messages": messages})
    reply = result["messages"][-1].content

    # 5. Enviar respuesta por el mismo canal
    client = GHLClient(location["private_integration_token"])
    try:
        await client.send_message(contact_id, reply, channel=channel)
    finally:
        await client.aclose()

    # 6. Persistir (alimenta transcripts + metering)
    await append_message(conversation["id"], "user", text)
    await append_message(conversation["id"], "assistant", reply)
    # TODO: record_usage(location_id, tokens) para billing
