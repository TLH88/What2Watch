from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.title import Title
from app.models.user import UserWatchlistItem

router = APIRouter()


@router.get("/watchlist")
async def get_watchlist(
    user_id: int = Query(...),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get user's watchlist with title details."""
    query = (
        select(
            UserWatchlistItem.id,
            UserWatchlistItem.status,
            UserWatchlistItem.added_at,
            Title.tmdb_id,
            Title.title,
            Title.media_type,
            Title.poster_path,
            Title.vote_average,
            Title.overview,
            Title.release_date,
            Title.runtime,
        )
        .join(Title, UserWatchlistItem.title_id == Title.id)
        .where(UserWatchlistItem.user_id == user_id)
    )
    if status:
        query = query.where(UserWatchlistItem.status == status)
    query = query.order_by(UserWatchlistItem.added_at.desc())

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": row.id,
            "status": row.status,
            "added_at": row.added_at.isoformat() if row.added_at else None,
            "tmdb_id": row.tmdb_id,
            "title": row.title,
            "media_type": row.media_type,
            "poster_path": row.poster_path,
            "vote_average": row.vote_average,
            "overview": row.overview,
            "year": str(row.release_date.year) if row.release_date else None,
            "runtime": row.runtime,
        }
        for row in rows
    ]


@router.patch("/watchlist/{item_id}")
async def update_watchlist_item(
    item_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Update watchlist item status (saved, watching, watched)."""
    result = await db.execute(
        select(UserWatchlistItem).where(UserWatchlistItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        return {"status": "not_found"}

    if "status" in data and data["status"] in ("saved", "watching", "watched"):
        item.status = data["status"]
        await db.commit()

    return {"status": "updated", "new_status": item.status}


@router.delete("/watchlist/{item_id}")
async def remove_watchlist_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove item from watchlist."""
    result = await db.execute(
        select(UserWatchlistItem).where(UserWatchlistItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        return {"status": "not_found"}

    await db.delete(item)
    await db.commit()
    return {"status": "removed"}
