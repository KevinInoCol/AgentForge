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

    # Google (OAuth para conexiones: Calendar, etc.). Se configura una sola app
    # de Google Cloud a nivel plataforma; cada tenant conecta SU cuenta vía OAuth.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""  # p.ej. http://localhost:8000/oauth/google/callback

    # Cifrado de credenciales de terceros (tokens OAuth) guardadas en DB.
    # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # URL del panel (Next.js) para redirigir de vuelta tras el OAuth.
    frontend_url: str = "http://localhost:3000"

    # Buffer / debounce (ver skill message-concatenation-buffer)
    # Default False: requiere Redis. Actívalo (BUFFER_ENABLED=true + REDIS_URL) cuando lo montes.
    buffer_enabled: bool = False
    buffer_window_seconds: int = 8
    buffer_ttl_seconds: int = 300
    buffer_separator: str = "\n"

    # App
    app_env: str = "development"


settings = Settings()
