"""Análisis de conversaciones (por qué el contacto no avanzó con la compra).

- analyze_conversation: solo el análisis (bajo demanda).
- generate_followup_with_analysis: mensaje de seguimiento + análisis en UNA llamada
  (lo usa el Agente de Seguimiento IA, para no pagar dos veces).
"""
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from app.chat_history.supabase_store import load_history


class ConversationAnalysis(BaseModel):
    reason: str = Field(description="Por qué el contacto no avanzó con la compra/servicio")
    objection: str = Field(description="La objeción o duda principal detectada")
    recommendation: str = Field(description="Recomendación concreta para recuperarlo")


class FollowupWithAnalysis(ConversationAnalysis):
    message: str = Field(description="Mensaje de seguimiento breve y persuasivo para enviar")


_ANALYST = (
    "Eres un analista experto en ventas. Analizas la conversación de un contacto que NO avanzó "
    "con la compra del producto/servicio. Sé conciso y concreto, en español."
)


def _llm(model: str, api_key: str, temperature: float = 0.3):
    return init_chat_model(f"openai:{model}", temperature=temperature, api_key=api_key)


async def analyze_conversation(conversation_id: str, persona: str, model: str, api_key: str) -> dict:
    history = await load_history(conversation_id, limit=40)
    structured = _llm(model, api_key, 0.2).with_structured_output(ConversationAnalysis)
    res = await structured.ainvoke(
        [{"role": "system", "content": _ANALYST + "\n\nContexto del negocio:\n" + (persona or "")}]
        + history
        + [{"role": "user", "content": "Analiza por qué este contacto no avanzó con la compra."}]
    )
    return res.model_dump()


async def generate_followup_with_analysis(
    history: list[dict], persona: str, model: str, api_key: str, attempt: int
) -> dict:
    system = (
        _ANALYST + " Además del análisis, redacta UN mensaje de seguimiento breve (1-3 frases), "
        "cálido y persuasivo para retomar y cerrar, hablando como el asistente del negocio. "
        "No te repitas respecto a seguimientos anteriores.\n\nContexto del negocio:\n" + (persona or "")
    )
    structured = _llm(model, api_key, 0.6).with_structured_output(FollowupWithAnalysis)
    res = await structured.ainvoke(
        [{"role": "system", "content": system}]
        + history
        + [{"role": "user", "content": f"(Seguimiento #{attempt + 1}: pasaron horas sin respuesta.)"}]
    )
    return res.model_dump()
