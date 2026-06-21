"""Genera la config de un asistente a partir de una descripción del negocio.

Alimenta el flujo "Generate Assistant" del panel. Usa salida estructurada
(with_structured_output) para devolver {name, system_prompt} validado.

API verificada en docs oficiales (jun 2026):
  /oss/python/langchain/structured-output  → model.with_structured_output(PydanticModel)
"""
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

_META_PROMPT = """Eres un experto en diseñar agentes conversacionales de TEXTO para negocios.
A partir del nombre y la descripción que da el usuario, redacta un system prompt
en español, claro y accionable, usando este framework de etiquetas XML:

<Identidad> ... </Identidad>
<Personalidad> ... </Personalidad>
<Rol> ... </Rol>
<Objetivo_Principal> ... </Objetivo_Principal>
<Instrucciones_Generales> ... </Instrucciones_Generales>
<Formato_De_Respuesta> mensajes cortos, naturales, es un chat </Formato_De_Respuesta>
<Cierre_Seguro> deriva a un humano si algo está fuera de alcance </Cierre_Seguro>

Reglas:
- El agente es de texto (WhatsApp/SMS), nunca de voz.
- No inventa datos; si no sabe, ofrece derivar a un humano.
- Devuelve un nombre corto y descriptivo si el usuario no dio uno claro."""


class GeneratedAgent(BaseModel):
    """Borrador de asistente generado por IA."""

    name: str = Field(description="Nombre corto del asistente")
    system_prompt: str = Field(description="System prompt completo con etiquetas XML")


async def generate_agent(
    name: str, description: str, model: str = "gpt-4.1", api_key: str | None = None
) -> dict:
    kwargs = {"temperature": 0.4}
    if api_key:
        kwargs["api_key"] = api_key
    llm = init_chat_model(f"openai:{model}", **kwargs)
    structured = llm.with_structured_output(GeneratedAgent)
    result = await structured.ainvoke(
        [
            {"role": "system", "content": _META_PROMPT},
            {
                "role": "user",
                "content": f"Nombre (puede estar vacío): {name}\n\nDescripción del negocio/objetivo:\n{description}",
            },
        ]
    )
    return result.model_dump()
