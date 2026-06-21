"""Construye un agente LangChain DINÁMICAMENTE a partir de la config del tenant.

Diferencia clave con un agente 1-a-1: aquí no hay YAML fijo. La config viene de
Supabase (tabla `agents`) y se ensambla por cada conversación. Los YAMLs de
model_config/ y prompt/ son solo DEFAULTS para crear agentes nuevos.

API verificada en docs oficiales (jun 2026):
  - create_agent: /oss/python/langchain/agents
  - init_chat_model: /oss/python/langchain/models
"""
from dataclasses import dataclass, field

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.config import settings


def resolve_openai_key(location: dict | None) -> str | None:
    """Usa la key de la sub-cuenta si existe; si no, la global de ARIA (.env)."""
    if location and location.get("openai_api_key"):
        return location["openai_api_key"]
    return settings.openai_api_key or None


@dataclass
class TenantAgentConfig:
    agent_id: str
    location_id: str
    system_prompt: str
    model: str = "gpt-4.1"
    temperature: float = 0.0
    tools: list[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict) -> "TenantAgentConfig":
        return cls(
            agent_id=row["id"],
            location_id=row["location_id"],
            system_prompt=row["system_prompt"],
            model=row.get("model", "gpt-4.1"),
            temperature=row.get("temperature", 0.0),
            tools=row.get("tools", []),
        )


def build_agent(cfg: TenantAgentConfig, api_key: str | None = None):
    """Devuelve un agente LangChain listo para .ainvoke({"messages": [...]}).

    `api_key`: API key de OpenAI a usar (la de la sub-cuenta). Si es None,
    init_chat_model cae a la variable de entorno OPENAI_API_KEY.

    MVP: sin tools ni RAG (Fase 1). En fases siguientes se inyectan las tools de
    app/tools/ (ligadas al tenant) y el retriever de app/RAG/.
    """
    kwargs = {"temperature": cfg.temperature}
    if api_key:
        kwargs["api_key"] = api_key
    model = init_chat_model(f"openai:{cfg.model}", **kwargs)
    return create_agent(
        model=model,
        tools=[],  # Fase 1: sin tools todavía
        system_prompt=cfg.system_prompt,
    )
