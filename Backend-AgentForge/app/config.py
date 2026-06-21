"""Configuración central (lee del entorno). No poner lógica de negocio aquí."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    database_url: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # GoHighLevel (MVP usa PIT por sub-cuenta; OAuth queda para la fase de escala)
    ghl_client_id: str = ""
    ghl_client_secret: str = ""
    ghl_redirect_uri: str = ""
    ghl_webhook_secret: str = ""
    ghl_api_version: str = "2021-04-15"  # header Version para Conversations API v2

    # Buffer / debounce (ver skill message-concatenation-buffer)
    buffer_enabled: bool = True
    buffer_window_seconds: int = 8
    buffer_ttl_seconds: int = 300
    buffer_separator: str = "\n"

    # App
    app_env: str = "development"


settings = Settings()
