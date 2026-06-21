"""Persistencia de la conversación en Supabase (tablas `conversations` y `messages`).

Backend intercambiable: runtime.py nunca sabe que es Supabase.
supabase-py v2 es síncrono → se envuelve en asyncio.to_thread.
"""
import asyncio

from app.db.supabase import get_supabase


async def get_or_create_conversation(location_id: str, contact_id: str) -> dict:
    """Devuelve la conversación (la crea si no existe). Incluye human_handoff."""
    def _get():
        return (
            get_supabase()
            .table("agentforge_conversations")
            .select("*")
            .eq("location_id", location_id)
            .eq("ghl_contact_id", contact_id)
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_get)
    if res.data:
        return res.data[0]

    def _insert():
        return (
            get_supabase()
            .table("agentforge_conversations")
            .insert({"location_id": location_id, "ghl_contact_id": contact_id})
            .execute()
        )

    res = await asyncio.to_thread(_insert)
    return res.data[0]


async def load_history(conversation_id: str, limit: int = 30) -> list[dict]:
    """Últimos mensajes como [{role, content}, ...] en orden cronológico."""
    def _q():
        return (
            get_supabase()
            .table("agentforge_messages")
            .select("role, content, created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    rows = list(reversed(res.data or []))
    return [{"role": r["role"], "content": r["content"]} for r in rows]


async def append_message(
    conversation_id: str, role: str, content: str, tokens: int = 0
) -> None:
    """Guarda un mensaje. `tokens` alimenta el metering de billing."""
    def _insert():
        return (
            get_supabase()
            .table("agentforge_messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "tokens": tokens,
                }
            )
            .execute()
        )

    await asyncio.to_thread(_insert)
