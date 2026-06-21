"""RAG · Etapa 4 — Vector store (pgvector en Supabase).

Persiste los fragmentos+embeddings y hace la búsqueda por similitud (RPC).
Aísla todo el acceso a la base vectorial; para cambiar de motor (Qdrant, Pinecone,
pgvector con hnsw, etc.) solo se toca este módulo.
"""
import asyncio

from app.db.supabase import get_supabase

CHUNKS_TABLE = "agentforge_knowledge_chunks"
MATCH_FN = "match_agentforge_chunks"


async def store_chunks(
    agent_id: str,
    document_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    rows = [
        {"agent_id": agent_id, "document_id": document_id, "content": c, "embedding": e}
        for c, e in zip(chunks, embeddings)
    ]

    def _q():
        return get_supabase().table(CHUNKS_TABLE).insert(rows).execute()

    await asyncio.to_thread(_q)


async def similarity_search(agent_id: str, query_embedding: list[float], k: int = 5) -> list[dict]:
    def _q():
        return get_supabase().rpc(
            MATCH_FN,
            {"p_agent_id": agent_id, "p_query_embedding": query_embedding, "p_match_count": k},
        ).execute()

    res = await asyncio.to_thread(_q)
    return res.data or []
