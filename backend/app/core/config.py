from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "What2Watch"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://what2watch:what2watch@localhost:5432/what2watch"

    # CORS - allow LAN access
    cors_origins: list[str] = ["*"]

    # API keys (loaded from .env)
    tmdb_api_key: str = ""
    trakt_client_id: str = ""
    trakt_client_secret: str = ""
    jellyfin_url: str = ""
    jellyfin_api_key: str = ""

    # AI providers
    ai_provider: str = "openai"  # openai | anthropic | google
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""

    # App secret
    secret_key: str = "change-me-in-production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
