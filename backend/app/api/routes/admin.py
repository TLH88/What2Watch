import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.title import Title, TitleLocalAvailability
from app.models.user import LanguagePreference, User, UserFeedback, UserWatchHistory, UserWatchlistItem
from app.services.integrations.tmdb import tmdb_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


@router.get("/status")
async def admin_status(db: AsyncSession = Depends(get_db)):
    """System health and stats overview."""
    # Database stats
    title_count = (await db.execute(select(func.count(Title.id)))).scalar() or 0
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    feedback_count = (await db.execute(select(func.count(UserFeedback.id)))).scalar() or 0
    watch_count = (await db.execute(select(func.count(UserWatchHistory.id)))).scalar() or 0
    watchlist_count = (await db.execute(select(func.count(UserWatchlistItem.id)))).scalar() or 0
    local_count = (await db.execute(select(func.count(TitleLocalAvailability.id)))).scalar() or 0

    # Source health checks
    sources = {}

    # TMDB
    try:
        tmdb_ok = await tmdb_client.test_connection()
        sources["tmdb"] = {"status": "connected" if tmdb_ok else "error"}
    except Exception as e:
        sources["tmdb"] = {"status": "error", "detail": str(e)}

    # Jellyfin
    try:
        from app.services.integrations.jellyfin import jellyfin_client
        from app.core.config import settings
        if settings.jellyfin_url and settings.jellyfin_api_key:
            jf_ok = await jellyfin_client.test_connection()
            sources["jellyfin"] = {"status": "connected" if jf_ok else "error"}
        else:
            sources["jellyfin"] = {"status": "not_configured"}
    except Exception as e:
        sources["jellyfin"] = {"status": "error", "detail": str(e)}

    # Trakt
    try:
        from app.core.config import settings
        if settings.trakt_client_id:
            sources["trakt"] = {"status": "configured"}
        else:
            sources["trakt"] = {"status": "not_configured"}
    except Exception:
        sources["trakt"] = {"status": "not_configured"}

    # AI provider
    try:
        from app.services.ai.provider import test_ai_provider
        ai_status = await test_ai_provider()
        sources["ai"] = ai_status
    except Exception as e:
        sources["ai"] = {"status": "error", "detail": str(e)}

    # Database connectivity
    try:
        await db.execute(text("SELECT 1"))
        sources["database"] = {"status": "connected"}
    except Exception as e:
        sources["database"] = {"status": "error", "detail": str(e)}

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "titles": title_count,
            "users": user_count,
            "feedback": feedback_count,
            "watch_history": watch_count,
            "watchlist": watchlist_count,
            "local_availability": local_count,
        },
        "sources": sources,
    }


@router.post("/refresh-metadata")
async def refresh_metadata(db: AsyncSession = Depends(get_db)):
    """Re-fetch metadata from TMDB for all stored titles."""
    from app.services.title_service import fetch_and_store_title

    result = await db.execute(select(Title.tmdb_id, Title.media_type))
    titles = result.all()
    updated = 0
    errors = 0
    for tmdb_id, media_type in titles:
        try:
            await fetch_and_store_title(db, tmdb_id, media_type, force_refresh=True)
            updated += 1
        except Exception:
            errors += 1
            logger.warning(f"Failed to refresh tmdb_id={tmdb_id}")

    return {"status": "ok", "updated": updated, "errors": errors}


@router.post("/sync/jellyfin")
async def sync_jellyfin(db: AsyncSession = Depends(get_db)):
    """Re-sync local availability from Jellyfin."""
    from app.services.integrations.jellyfin import sync_jellyfin_availability

    try:
        count = await sync_jellyfin_availability(db)
        return {"status": "ok", "matched": count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/sync/trakt")
async def sync_trakt_all(db: AsyncSession = Depends(get_db)):
    """Sync Trakt watch history for all connected users."""
    from app.services.integrations.trakt import sync_trakt_history

    result = await db.execute(
        select(User.id).join(User.preferences).where(
            User.preferences.has(trakt_connected=True)
        )
    )
    user_ids = [row[0] for row in result.all()]
    total = 0
    for uid in user_ids:
        try:
            count = await sync_trakt_history(db, uid)
            total += count
        except Exception:
            logger.warning(f"Trakt sync failed for user {uid}")

    return {"status": "ok", "users_synced": len(user_ids), "imported": total}


@router.get("/languages")
async def get_language_preferences(db: AsyncSession = Depends(get_db)):
    """Get configured language preferences."""
    result = await db.execute(
        select(LanguagePreference).order_by(LanguagePreference.priority)
    )
    langs = result.scalars().all()
    return [
        {"id": lp.id, "language_code": lp.language_code, "language_name": lp.language_name, "priority": lp.priority}
        for lp in langs
    ]


@router.put("/languages")
async def update_language_preferences(data: dict, db: AsyncSession = Depends(get_db)):
    """Set language preferences (up to 5). Replaces all existing preferences.

    Expected: {"languages": [{"code": "en", "name": "English"}, ...]}
    """
    languages = data.get("languages", [])
    if len(languages) > 5:
        return {"status": "error", "detail": "Maximum 5 language preferences allowed"}

    # Clear existing
    await db.execute(select(LanguagePreference))  # ensure table is loaded
    existing = (await db.execute(select(LanguagePreference))).scalars().all()
    for lp in existing:
        await db.delete(lp)

    # Insert new
    for i, lang in enumerate(languages):
        code = lang.get("code", "").strip().lower()
        name = lang.get("name", "").strip()
        if not code or not name:
            continue
        db.add(LanguagePreference(language_code=code, language_name=name, priority=i))

    await db.commit()
    return {"status": "ok", "count": len(languages)}


@router.get("/ai-settings")
async def get_ai_settings():
    """Get current AI provider configuration."""
    from app.services.ai.provider import test_ai_provider
    status = await test_ai_provider()
    return status


@router.put("/ai-settings")
async def update_ai_settings(data: dict):
    """Switch AI provider at runtime."""
    provider = data.get("provider")
    if provider not in ("openai", "anthropic", "google"):
        return {"status": "error", "detail": "Invalid provider. Must be: openai, anthropic, google"}

    from app.services.ai.provider import set_ai_provider
    success = set_ai_provider(provider)
    if success:
        return {"status": "ok", "provider": provider}
    return {"status": "error", "detail": f"Failed to switch to {provider}. Check API key."}


# --- API Key Management ---

API_KEY_FIELDS = [
    {"name": "openai_api_key", "label": "OpenAI API Key"},
    {"name": "anthropic_api_key", "label": "Anthropic API Key"},
    {"name": "google_ai_api_key", "label": "Google AI API Key"},
    {"name": "tmdb_api_key", "label": "TMDB API Key"},
    {"name": "trakt_client_id", "label": "Trakt Client ID"},
    {"name": "trakt_client_secret", "label": "Trakt Client Secret"},
    {"name": "jellyfin_url", "label": "Jellyfin URL"},
    {"name": "jellyfin_api_key", "label": "Jellyfin API Key"},
]

AI_KEY_FIELDS = {"openai_api_key", "anthropic_api_key", "google_ai_api_key"}


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


@router.get("/api-keys")
async def get_api_keys():
    """Return all configurable API keys with masked values."""
    from app.core.config import settings

    keys = []
    for field in API_KEY_FIELDS:
        value = getattr(settings, field["name"], "")
        keys.append({
            "name": field["name"],
            "label": field["label"],
            "masked": _mask(value),
            "configured": bool(value),
        })
    return {"keys": keys}


@router.put("/api-keys")
async def update_api_keys(data: dict):
    """Update one or more API keys. Persists to .env and updates runtime settings."""
    from app.core.config import settings, update_env_file, ENV_KEY_MAP

    keys_to_update = data.get("keys", {})
    if not keys_to_update:
        return {"status": "error", "detail": "No keys provided"}

    valid_names = {f["name"] for f in API_KEY_FIELDS}
    updated = []
    env_updates = {}

    for name, value in keys_to_update.items():
        if name not in valid_names:
            continue
        # Update in-memory settings
        setattr(settings, name, value)
        # Map to .env variable name
        env_var = ENV_KEY_MAP.get(name)
        if env_var:
            env_updates[env_var] = value
        updated.append(name)

    # Persist to .env file
    if env_updates:
        update_env_file(env_updates)

    # Reinitialize AI provider if an AI key was changed
    if AI_KEY_FIELDS & set(updated):
        try:
            from app.services.ai.provider import set_ai_provider
            set_ai_provider(settings.ai_provider)
        except Exception:
            logger.warning("Failed to reinitialize AI provider after key update")

    return {"status": "ok", "updated": updated}
