"""RAG · Orquestador.

Encadena las etapas del pipeline. Cada etapa vive en su propio módulo, así
sabemos qué tenemos y podemos mejorar cada una por separado (mejor parser,
otro chunking, otro modelo de embeddings, otro vector store).

  1. extraction   → texto plano (PDF/TXT)
  2. chunking     → fragmentos
  3. embedding    → vectores
  4. vector_store → persistir en pgvector
"""
import logging

from app.RAG.chunking import chunk_text
from app.RAG.embedding import embed_texts
from app.RAG.extraction import extract_text
from app.RAG.vector_store import store_chunks
from app.db.queries import insert_document

logger = logging.getLogger(__name__)


async def ingest_document(agent_id: str, filename: str, data: bytes, api_key: str) -> int:
    """Procesa un documento por todas las etapas. Devuelve nº de fragmentos."""
    text = extract_text(filename, data)            # 1. Extracción
    if not text:
        return 0

    chunks = chunk_text(text)                       # 2. Chunking
    if not chunks:
        return 0

    embeddings = await embed_texts(chunks, api_key)  # 3. Embeddings
    doc = await insert_document(agent_id, filename)  # metadata del documento
    await store_chunks(agent_id, doc["id"], chunks, embeddings)  # 4. Vector store

    logger.warning("[kb] '%s' indexado: %d fragmentos (agente %s)", filename, len(chunks), agent_id)
    return len(chunks)
