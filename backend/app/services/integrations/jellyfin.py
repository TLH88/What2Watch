import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.title import Title, TitleExternalId, TitleLocalAvailability

logger = logging.getLogger(__name__)


class JellyfinClient:
    def __init__(self):
        self.base_url = settings.jellyfin_url.rstrip("/") if settings.jellyfin_url else ""
        self.api_key = settings.jellyfin_api_key

    @property
    def headers(self):
        return {"X-Emby-Token": self.api_key}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}{path}",
                headers=self.headers,
                params=params or {},
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> bool:
        if not self.base_url:
            return False
        try:
            data = await self._get("/System/Info/Public")
            return "ServerName" in data
        except Exception:
            logger.exception("Jellyfin connection test failed")
            return False

    async def get_libraries(self) -> list[dict]:
        data = await self._get("/Library/VirtualFolders")
        return data

    async def get_items(
        self,
        library_id: str | None = None,
        media_type: str = "Movie",
        start_index: int = 0,
        limit: int = 100,
    ) -> dict:
        params = {
            "IncludeItemTypes": media_type,
            "Recursive": "true",
            "Fields": "ProviderIds,Path,MediaSources",
            "StartIndex": start_index,
            "Limit": limit,
        }
        if library_id:
            params["ParentId"] = library_id
        return await self._get("/Items", params)

    async def get_all_items(self, media_type: str = "Movie") -> list[dict]:
        all_items = []
        start = 0
        limit = 200
        while True:
            data = await self.get_items(media_type=media_type, start_index=start, limit=limit)
            items = data.get("Items", [])
            all_items.extend(items)
            if start + limit >= data.get("TotalRecordCount", 0):
                break
            start += limit
        return all_items


jellyfin_client = JellyfinClient()


async def sync_jellyfin_availability(db: AsyncSession) -> int:
    """Sync local availability from Jellyfin. Returns count of matched titles."""
    matched = 0

    for jf_type, media_type in [("Movie", "movie"), ("Series", "tv")]:
        try:
            items = await jellyfin_client.get_all_items(media_type=jf_type)
        except Exception:
            logger.exception(f"Failed to fetch Jellyfin {jf_type} items")
            continue

        for item in items:
            provider_ids = item.get("ProviderIds", {})
            tmdb_id = provider_ids.get("Tmdb")
            imdb_id = provider_ids.get("Imdb")

            if not tmdb_id and not imdb_id:
                continue

            # Try to find matching title by TMDB ID first
            title = None
            if tmdb_id:
                result = await db.execute(
                    select(Title).where(Title.tmdb_id == int(tmdb_id))
                )
                title = result.scalar_one_or_none()

            # Fall back to IMDb ID lookup
            if not title and imdb_id:
                result = await db.execute(
                    select(Title)
                    .join(TitleExternalId)
                    .where(
                        TitleExternalId.source == "imdb",
                        TitleExternalId.external_id == imdb_id,
                    )
                )
                title = result.scalar_one_or_none()

            if not title:
                continue

            # Check if availability already recorded
            existing = await db.execute(
                select(TitleLocalAvailability).where(
                    TitleLocalAvailability.title_id == title.id,
                    TitleLocalAvailability.source == "jellyfin",
                    TitleLocalAvailability.source_item_id == item["Id"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            avail = TitleLocalAvailability(
                title_id=title.id,
                source="jellyfin",
                source_item_id=item["Id"],
                library_name=item.get("ParentName") or item.get("SeriesName"),
                file_path=item.get("Path"),
                available=True,
            )
            db.add(avail)
            matched += 1

    await db.commit()
    return matched
