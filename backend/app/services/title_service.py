import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.title import (
    Title,
    TitleExternalId,
    TitleGenre,
    TitlePerson,
    TitleVideo,
    TitleWatchProvider,
)
from app.services.integrations.tmdb import (
    parse_credits,
    parse_external_ids,
    parse_genres,
    parse_movie_to_title_data,
    parse_tv_to_title_data,
    parse_videos,
    parse_watch_providers,
    tmdb_client,
)

logger = logging.getLogger(__name__)


async def get_title_by_tmdb_id(db: AsyncSession, tmdb_id: int) -> Title | None:
    result = await db.execute(
        select(Title)
        .where(Title.tmdb_id == tmdb_id)
        .options(
            selectinload(Title.genres),
            selectinload(Title.external_ids),
            selectinload(Title.people),
            selectinload(Title.videos),
            selectinload(Title.watch_providers),
            selectinload(Title.local_availability),
        )
    )
    return result.scalar_one_or_none()


async def fetch_and_store_title(
    db: AsyncSession, tmdb_id: int, media_type: str, force_refresh: bool = False,
) -> Title:
    """Fetch full title details from TMDB and persist to database."""
    existing = await get_title_by_tmdb_id(db, tmdb_id)
    if existing and not force_refresh:
        return existing

    if media_type == "movie":
        data = await tmdb_client.get_movie(tmdb_id)
        title_data = parse_movie_to_title_data(data)
    else:
        data = await tmdb_client.get_tv(tmdb_id)
        title_data = parse_tv_to_title_data(data)

    # Parse release_date string to date object
    rd = title_data.pop("release_date", None)
    if rd and isinstance(rd, str):
        try:
            title_data["release_date"] = date.fromisoformat(rd)
        except ValueError:
            title_data["release_date"] = None
    else:
        title_data["release_date"] = rd

    if existing and force_refresh:
        # Update existing title fields
        for key, value in title_data.items():
            if key != "tmdb_id":
                setattr(existing, key, value)
        await db.commit()
        return await get_title_by_tmdb_id(db, tmdb_id)

    title = Title(**title_data)

    # Genres
    for g in parse_genres(data):
        title.genres.append(TitleGenre(**g))

    # Credits
    for p in parse_credits(data):
        title.people.append(TitlePerson(**p))

    # Videos
    for v in parse_videos(data):
        title.videos.append(TitleVideo(**v))

    # Watch providers
    for wp in parse_watch_providers(data):
        title.watch_providers.append(TitleWatchProvider(**wp))

    # External IDs
    for eid in parse_external_ids(data):
        title.external_ids.append(TitleExternalId(**eid))

    db.add(title)
    await db.commit()
    await db.refresh(title)

    # Reload with relationships
    return await get_title_by_tmdb_id(db, tmdb_id)


async def search_titles(query: str, media_type: str | None = None, page: int = 1) -> dict:
    """Search TMDB for titles. Returns raw search results (not stored)."""
    if media_type == "movie":
        data = await tmdb_client.search_movie(query, page=page)
    elif media_type == "tv":
        data = await tmdb_client.search_tv(query, page=page)
    else:
        data = await tmdb_client.search_multi(query, page=page)

    results = []
    for item in data.get("results", []):
        mt = item.get("media_type", media_type or "movie")
        if mt not in ("movie", "tv"):
            continue
        results.append({
            "tmdb_id": item["id"],
            "media_type": mt,
            "title": item.get("title") or item.get("name", ""),
            "overview": item.get("overview"),
            "poster_path": item.get("poster_path"),
            "release_date": item.get("release_date") or item.get("first_air_date"),
            "vote_average": item.get("vote_average"),
            "popularity": item.get("popularity"),
        })

    return {
        "results": results,
        "total_results": data.get("total_results", 0),
        "total_pages": data.get("total_pages", 0),
        "page": data.get("page", 1),
    }
