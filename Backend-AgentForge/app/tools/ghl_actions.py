"""Tools que el agente puede llamar. Una acción = una tool.

Cada factory recibe el contexto del tenant (location_id / cliente GHL) para que
la tool actúe SOLO sobre la sub-cuenta correcta. El name/description son el
contrato de la tool (no van en el prompt).
"""
from langchain_core.tools import StructuredTool

from app.integrations.ghl.client import get_client_for_location


def get_tools_for_agent(location_id: str, enabled: list[str]) -> list:
    """Devuelve las tools habilitadas para este agente, ya ligadas al tenant."""
    registry = {
        "add_tag": _make_add_tag_tool(location_id),
        "book_appointment": _make_booking_tool(location_id),
        # "update_custom_field": ...
    }
    return [registry[name] for name in enabled if name in registry]


def _make_add_tag_tool(location_id: str) -> StructuredTool:
    async def add_tag(contact_id: str, tag: str) -> str:
        client = await get_client_for_location(location_id)
        await client.add_tag(contact_id, tag)
        return f"tag '{tag}' agregado"

    return StructuredTool.from_function(
        coroutine=add_tag,
        name="add_tag",
        description="Agrega una etiqueta (tag) a un contacto en GoHighLevel.",
    )


def _make_booking_tool(location_id: str) -> StructuredTool:
    async def book(calendar_id: str, contact_id: str, slot: str) -> str:
        client = await get_client_for_location(location_id)
        await client.book_appointment(calendar_id, contact_id, slot)
        return "cita agendada"

    return StructuredTool.from_function(
        coroutine=book,
        name="book_appointment",
        description="Agenda una cita en un calendario de GoHighLevel.",
    )
