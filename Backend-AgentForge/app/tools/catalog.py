"""Catálogo único de tools + ensamblador para el agente de un tenant.

Este es el ÚNICO lugar donde se decide qué tools recibe un agente. Antes la
lógica estaba dispersa (knowledge en runtime, un registry GHL sin cablear). Ahora:

  - Cada tool "conectable" vive en TOOL_CATALOG con su metadata (label/descr) y
    una `factory(ctx)` que la construye ligada al tenant.
  - Algunas tools requieren una CONEXIÓN activa (OAuth): `provider` != None. Si el
    workspace no la conectó, la tool se omite (no rompe el turno).
  - La Base de Conocimiento sigue siendo AUTOMÁTICA (si el agente tiene documentos),
    no hace falta habilitarla.

Para agregar una tool nueva: registra un ToolSpec aquí. Nada más cambia.
"""
import logging
from dataclasses import dataclass
from typing import Callable

from app.db.queries import agent_has_knowledge, get_connection
from app.tools.calendar import get_calendar_tools
from app.tools.ghl_actions import _make_add_tag_tool, _make_booking_tool
from app.tools.knowledge import get_knowledge_tool

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolSpec:
    key: str
    label: str            # nombre para el usuario en el frontend
    description: str      # qué hace (para la UI, no para el prompt)
    factory: Callable     # factory(ctx: dict) -> list[StructuredTool]
    provider: str | None = None  # si requiere una conexión OAuth (agentforge_connections.provider)


# Registro de tools habilitables (las que el usuario prende por agente).
TOOL_CATALOG: dict[str, ToolSpec] = {
    "google_calendar": ToolSpec(
        key="google_calendar",
        label="Google Calendar",
        description="Consultar disponibilidad y agendar citas en Google Calendar.",
        provider="google_calendar",
        factory=lambda ctx: get_calendar_tools(ctx["connection"]),
    ),
    "add_tag": ToolSpec(
        key="add_tag",
        label="Etiquetar contacto (GHL)",
        description="Permite al agente agregar etiquetas a un contacto en GoHighLevel.",
        factory=lambda ctx: [_make_add_tag_tool(ctx["location_id"])],
    ),
    "book_appointment": ToolSpec(
        key="book_appointment",
        label="Agendar en calendario GHL",
        description="Agenda una cita en un calendario nativo de GoHighLevel.",
        factory=lambda ctx: [_make_booking_tool(ctx["location_id"])],
    ),
}


def catalog_public() -> list[dict]:
    """Metadata del catálogo para el frontend (sin factories)."""
    return [
        {"key": s.key, "label": s.label, "description": s.description, "provider": s.provider}
        for s in TOOL_CATALOG.values()
    ]


async def build_tools_for_agent(agent_row: dict, location: dict, api_key: str) -> list:
    """Ensambla TODAS las tools de un agente: knowledge (auto) + las habilitadas.

    `location` es la fila del workspace (para resolver conexiones y contexto GHL).
    """
    tools: list = []
    agent_id = agent_row["id"]
    location_id = location["id"]

    # 1. Base de conocimiento: automática si el agente tiene documentos.
    if await agent_has_knowledge(agent_id):
        tools.append(get_knowledge_tool(agent_id, api_key))

    # 2. Tools habilitadas por el usuario (columna agents.tools).
    for key in agent_row.get("tools") or []:
        spec = TOOL_CATALOG.get(key)
        if not spec:
            logger.warning("[tools] '%s' habilitada pero no existe en el catálogo", key)
            continue

        ctx = {"location_id": location_id, "agent_id": agent_id, "api_key": api_key}
        if spec.provider:
            conn = await get_connection(location_id, spec.provider)
            if not conn or conn.get("status") != "active":
                logger.warning(
                    "[tools] '%s' habilitada pero sin conexión activa de '%s'; se omite",
                    key, spec.provider,
                )
                continue
            ctx["connection"] = conn
        try:
            tools.extend(spec.factory(ctx))
        except Exception:  # noqa: BLE001
            logger.exception("[tools] error construyendo '%s'; se omite", key)

    return tools
