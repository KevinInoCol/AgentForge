"""Pipeline de indexación del knowledge base — POR TENANT.

Cada agente tiene su propio knowledge base. Los chunks se guardan en pgvector
con su `agent_id` (o `location_id`) para aislar el retrieval entre clientes.
Aquí va SOLO indexación; la config de retrieval (top_k) vive en tools/.
"""


async def index_document(agent_id: str, file_bytes: bytes, filename: str) -> int:
    """Carga, trocea, embebe y persiste un documento. Devuelve nº de chunks.

    TODO:
      - loader según tipo (pdf/txt/docx)
      - splitter (chunk_size / chunk_overlap)
      - embeddings (OpenAI) -> insertar en tabla `knowledge_chunks` con agent_id
    """
    raise NotImplementedError


def get_retriever(agent_id: str, top_k: int = 5):
    """Devuelve un retriever de pgvector FILTRADO por agent_id (aislamiento)."""
    # TODO: PGVector(...).as_retriever(search_kwargs={"k": top_k, "filter": {agent_id}})
    raise NotImplementedError
