"""Consultas a Supabase para locations y agents.

supabase-py v2 es síncrono; envolvemos en asyncio.to_thread para no bloquear el
event loop de FastAPI.
"""
import asyncio

from app.db.supabase import get_supabase


async def insert_workspace(name: str | None = None, owner_user_id: str | None = None) -> dict:
    """Crea un workspace (tenant) vacío — solo para construir/probar agentes."""
    def _q():
        return (
            get_supabase()
            .table("agentforge_locations")
            .insert({"name": name or "Mi workspace", "owner_user_id": owner_user_id})
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0]


async def get_location_by_owner(owner_user_id: str) -> dict | None:
    def _q():
        return (
            get_supabase()
            .table("agentforge_locations")
            .select("*")
            .eq("owner_user_id", owner_user_id)
            .order("created_at")
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0] if res.data else None


async def update_location_row(location_id: str, values: dict) -> dict:
    """Actualiza un workspace/location por su id interno."""
    def _q():
        return (
            get_supabase()
            .table("agentforge_locations")
            .update(values)
            .eq("id", location_id)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0]


async def upsert_location(values: dict) -> dict:
    """Crea o actualiza una sub-cuenta por su ghl_location_id."""
    def _q():
        return (
            get_supabase()
            .table("agentforge_locations")
            .upsert(values, on_conflict="ghl_location_id")
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0]


async def get_location_by_ghl_id(ghl_location_id: str) -> dict | None:
    def _q():
        return (
            get_supabase()
            .table("agentforge_locations")
            .select("*")
            .eq("ghl_location_id", ghl_location_id)
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0] if res.data else None


async def get_location_by_id(location_id: str) -> dict | None:
    def _q():
        return (
            get_supabase()
            .table("agentforge_locations")
            .select("*")
            .eq("id", location_id)
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0] if res.data else None


async def get_active_agent_for_location(location_id: str) -> dict | None:
    """Devuelve el agente PUBLICADO y activo de la sub-cuenta (el que responde
    mensajes reales). Un borrador no contesta a leads."""
    def _q():
        return (
            get_supabase()
            .table("agentforge_agents")
            .select("*")
            .eq("location_id", location_id)
            .eq("enabled", True)
            .eq("published", True)
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0] if res.data else None


# ── CRUD de agentes (consumido por el frontend) ──────────────────────

async def list_agents_for_location(location_id: str) -> list[dict]:
    def _q():
        return (
            get_supabase()
            .table("agentforge_agents")
            .select("*")
            .eq("location_id", location_id)
            .order("created_at")
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data or []


async def get_agent(agent_id: str) -> dict | None:
    def _q():
        return (
            get_supabase().table("agentforge_agents").select("*").eq("id", agent_id).limit(1).execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0] if res.data else None


async def create_agent_row(values: dict) -> dict:
    def _q():
        return get_supabase().table("agentforge_agents").insert(values).execute()

    res = await asyncio.to_thread(_q)
    return res.data[0]


async def update_agent_row(agent_id: str, values: dict) -> dict:
    def _q():
        return (
            get_supabase().table("agentforge_agents").update(values).eq("id", agent_id).execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0]


async def delete_agent_row(agent_id: str) -> None:
    def _q():
        return get_supabase().table("agentforge_agents").delete().eq("id", agent_id).execute()

    await asyncio.to_thread(_q)


# ── Base de conocimiento (RAG) ───────────────────────────────────────

async def insert_document(agent_id: str, filename: str) -> dict:
    def _q():
        return (
            get_supabase()
            .table("agentforge_knowledge_documents")
            .insert({"agent_id": agent_id, "filename": filename})
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0]


async def list_documents(agent_id: str) -> list[dict]:
    def _q():
        return (
            get_supabase()
            .table("agentforge_knowledge_documents")
            .select("id, filename, created_at")
            .eq("agent_id", agent_id)
            .order("created_at", desc=True)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data or []


async def delete_document(document_id: str) -> None:
    def _q():
        # Los chunks se borran en cascada (FK on delete cascade).
        return get_supabase().table("agentforge_knowledge_documents").delete().eq("id", document_id).execute()

    await asyncio.to_thread(_q)


async def get_document(document_id: str) -> dict | None:
    def _q():
        return (
            get_supabase()
            .table("agentforge_knowledge_documents")
            .select("id, agent_id, filename")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return res.data[0] if res.data else None


async def workspace_contacts(workspace_id: str) -> list[dict]:
    """Contactos del workspace con nº de interacciones y última actividad."""
    def _q():
        return get_supabase().rpc(
            "agentforge_workspace_contacts", {"p_workspace_id": workspace_id}
        ).execute()

    res = await asyncio.to_thread(_q)
    return res.data or []


async def due_followups() -> list[dict]:
    """Conversaciones candidatas a recibir un seguimiento (RPC)."""
    def _q():
        return get_supabase().rpc("agentforge_due_followups", {}).execute()

    res = await asyncio.to_thread(_q)
    return res.data or []


async def agent_has_knowledge(agent_id: str) -> bool:
    def _q():
        return (
            get_supabase()
            .table("agentforge_knowledge_documents")
            .select("id")
            .eq("agent_id", agent_id)
            .limit(1)
            .execute()
        )

    res = await asyncio.to_thread(_q)
    return bool(res.data)
