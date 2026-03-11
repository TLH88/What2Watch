import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.title import Title, TitleLocalAvailability
from app.models.user import User, UserFeedback, UserWatchHistory, UserWatchlistItem
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
