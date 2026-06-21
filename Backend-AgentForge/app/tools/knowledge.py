"""Tool de retrieval: "Base de Conocimiento".

El agente la llama cuando el usuario pregunta algo específico del negocio.
Embebe la consulta, busca los fragmentos más parecidos (pgvector) del knowledge
base de ESE agente y se los devuelve para que responda con info real.

Nota: el nombre de tool de OpenAI no admite espacios/acentos, por eso es
`base_de_conocimiento`; de cara al agente representa la "Base de Conocimiento".
"""
import logging

from langchain_core.tools import StructuredTool

from app.core.embeddings import embed_query
from app.db.queries import match_chunks

logger = logging.getLogger(__name__)


def get_knowledge_tool(agent_id: str, api_key: str) -> StructuredTool:
    """Devuelve la tool de Base de Conocimiento ligada a este agente."""

    async def base_de_conocimiento(consulta: str) -> str:
        """Busca información del negocio en la Base de Conocimiento."""
        try:
            embedding = await embed_query(consulta, api_key)
            rows = await match_chunks(agent_id, embedding, k=5)
        except Exception:  # noqa: BLE001
            logger.exception("[kb] error buscando en la base de conocimiento")
            return "No se pudo consultar la base de conocimiento en este momento."

        if not rows:
            return "No hay información en la base de conocimiento sobre eso."
        return "\n\n---\n\n".join(r["content"] for r in rows)

    return StructuredTool.from_function(
        coroutine=base_de_conocimiento,
        name="base_de_conocimiento",
        description=(
            "Base de Conocimiento del negocio. Úsala SIEMPRE que el usuario pregunte "
            "algo específico (productos, precios, servicios, horarios, políticas, "
            "ubicación, promociones). Devuelve fragmentos reales; responde basándote en ellos."
        ),
    )
