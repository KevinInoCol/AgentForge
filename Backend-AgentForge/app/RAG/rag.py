"""Pipeline de indexación del knowledge base — POR AGENTE.

Sube un documento (PDF/TXT) → extrae texto → trocea → embeddings → guarda en
agentforge_knowledge_chunks (pgvector). La búsqueda vive en tools/knowledge.py.
"""
import io
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.embeddings import embed_texts
from app.db.queries import insert_chunks, insert_document

logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)


def extract_text(filename: str, data: bytes) -> str:
    """Extrae texto plano de un PDF o TXT."""
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return data.decode("utf-8", errors="replace")


async def ingest_document(agent_id: str, filename: str, data: bytes, api_key: str) -> int:
    """Procesa un documento y guarda sus fragmentos. Devuelve nº de chunks."""
    text = extract_text(filename, data).strip()
    if not text:
        return 0
    chunks = _splitter.split_text(text)
    if not chunks:
        return 0

    embeddings = await embed_texts(chunks, api_key)
    doc = await insert_document(agent_id, filename)
    await insert_chunks(agent_id, doc["id"], chunks, embeddings)
    logger.warning("[kb] documento '%s' indexado: %d fragmentos (agente %s)", filename, len(chunks), agent_id)
    return len(chunks)
