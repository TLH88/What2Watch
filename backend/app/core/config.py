import logging
from pathlib import Path

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Map settings field names to .env variable names
ENV_KEY_MAP: dict[str, str] = {
    "openai_api_key": "OPENAI_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "google_ai_api_key": "GOOGLE_AI_API_KEY",
    "tmdb_api_key": "TMDB_API_KEY",
    "trakt_client_id": "TRAKT_CLIENT_ID",
    "trakt_client_secret": "TRAKT_CLIENT_SECRET",
    "jellyfin_api_key": "JELLYFIN_API_KEY",
    "jellyfin_url": "JELLYFIN_URL",
    "ai_provider": "AI_PROVIDER",
}


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
    openai_model: str = "gpt-5.2"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    google_ai_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # App secret
    secret_key: str = "change-me-in-production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def update_env_file(updates: dict[str, str]) -> None:
    """Update .env file with new key-value pairs, preserving existing content."""
    env_path = Path(".env")
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Append any keys not already in the file
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info("Updated .env file with keys: %s", list(updates.keys()))
