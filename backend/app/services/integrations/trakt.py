import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.title import Title
from app.models.user import UserFeedback, UserPreferences, UserWatchHistory
from app.services.title_service import fetch_and_store_title

logger = logging.getLogger(__name__)

TRAKT_BASE_URL = "https://api.trakt.tv"


class TraktClient:
    def __init__(self):
        self.client_id = settings.trakt_client_id
        self.client_secret = settings.trakt_client_secret

    def _headers(self, access_token: str | None = None) -> dict:
        h = {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": self.client_id,
        }
        if access_token:
            h["Authorization"] = f"Bearer {access_token}"
        return h

    async def get_device_code(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{TRAKT_BASE_URL}/oauth/device/code",
                json={"client_id": self.client_id},
                headers=self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def poll_device_token(self, device_code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{TRAKT_BASE_URL}/oauth/device/token",
                json={
                    "code": device_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers=self._headers(),
                timeout=15.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"status": resp.status_code}

    async def get_watch_history(
        self, access_token: str, media_type: str = "movies", page: int = 1, limit: int = 100
    ) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TRAKT_BASE_URL}/sync/history/{media_type}",
                headers=self._headers(access_token),
                params={"page": page, "limit": limit},
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_ratings(self, access_token: str, media_type: str = "movies") -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TRAKT_BASE_URL}/sync/ratings/{media_type}",
                headers=self._headers(access_token),
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()


trakt_client = TraktClient()


async def sync_trakt_history(db: AsyncSession, user_id: int) -> int:
    """Import Trakt watch history for a user. Returns count of imported items."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs or not prefs.trakt_access_token:
        return 0

    imported = 0
    token = prefs.trakt_access_token

    for trakt_type, media_type in [("movies", "movie"), ("shows", "tv")]:
        try:
            history = await trakt_client.get_watch_history(
                token, media_type=trakt_type, limit=500
            )
        except Exception:
            logger.exception(f"Failed to fetch Trakt {trakt_type} history")
            continue

        for entry in history:
            item = entry.get(trakt_type.rstrip("s"), entry.get("show", {}))
            tmdb_id = item.get("ids", {}).get("tmdb")
            if not tmdb_id:
                continue

            # Check if already in watch history (any source)
            existing = await db.execute(
                select(UserWatchHistory).where(
                    UserWatchHistory.user_id == user_id,
                    UserWatchHistory.title_id == select(Title.id).where(Title.tmdb_id == tmdb_id).scalar_subquery(),
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Fetch and store the title if not already in DB
            try:
                title = await fetch_and_store_title(db, tmdb_id, media_type)
            except Exception:
                logger.warning(f"Could not fetch TMDB title {tmdb_id}")
                continue

            watched_at = None
            if entry.get("watched_at"):
                try:
                    dt = datetime.fromisoformat(
                        entry["watched_at"].replace("Z", "+00:00")
                    )
                    # Strip timezone info for naive TIMESTAMP column
                    watched_at = dt.replace(tzinfo=None)
                except ValueError:
                    pass

            watch_entry = UserWatchHistory(
                user_id=user_id,
                title_id=title.id,
                source="trakt",
                watched_at=watched_at,
            )
            db.add(watch_entry)
            imported += 1

    await db.commit()
    return imported


async def sync_trakt_ratings(db: AsyncSession, user_id: int) -> int:
    """Import Trakt ratings as UserFeedback. Returns count of imported ratings."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs or not prefs.trakt_access_token:
        return 0

    imported = 0
    token = prefs.trakt_access_token

    for trakt_type, media_type in [("movies", "movie"), ("shows", "tv")]:
        try:
            ratings = await trakt_client.get_ratings(token, media_type=trakt_type)
        except Exception:
            logger.exception(f"Failed to fetch Trakt {trakt_type} ratings")
            continue

        for entry in ratings:
            rating = entry.get("rating")
            if rating is None:
                continue

            # Map: >=6 thumbs_up, <6 thumbs_down
            if rating >= 6:
                feedback_type = "thumbs_up"
            else:
                feedback_type = "thumbs_down"

            item = entry.get(trakt_type.rstrip("s"), entry.get("show", {}))
            tmdb_id = item.get("ids", {}).get("tmdb")
            if not tmdb_id:
                continue

            # Fetch/store title
            try:
                title = await fetch_and_store_title(db, tmdb_id, media_type)
            except Exception:
                logger.warning(f"Could not fetch TMDB title {tmdb_id}")
                continue

            # Check if feedback already exists for this user+title
            existing = await db.execute(
                select(UserFeedback).where(
                    UserFeedback.user_id == user_id,
                    UserFeedback.title_id == title.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            fb = UserFeedback(
                user_id=user_id,
                title_id=title.id,
                feedback_type=feedback_type,
            )
            db.add(fb)
            imported += 1

    await db.commit()
    return imported
