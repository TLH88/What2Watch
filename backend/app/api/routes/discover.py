from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.discover import (
    DiscoverFeedbackRequest,
    DiscoverRespondRequest,
    DiscoverResponse,
    DiscoverStartRequest,
)
from app.services.discover_service import respond_discover, start_discover
from app.models.user import PendingRating, UserFeedback, UserWatchHistory, UserWatchlistItem
from app.models.title import Title
from sqlalchemy import select, and_

router = APIRouter()


@router.post("/discover/start", response_model=DiscoverResponse)
async def discover_start(
    data: DiscoverStartRequest,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await start_discover(
        db, user_id, data.query, data.media_type, data.genres
    )


@router.post("/discover/respond", response_model=DiscoverResponse)
async def discover_respond(
    data: DiscoverRespondRequest,
    db: AsyncSession = Depends(get_db),
):
    return await respond_discover(db, data.session_id, data.answer)


@router.post("/discover/feedback")
async def discover_feedback(
    data: DiscoverFeedbackRequest,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # Find the title
    result = await db.execute(
        select(Title).where(Title.tmdb_id == data.tmdb_id)
    )
    title = result.scalar_one_or_none()
    if not title:
        return {"status": "title_not_found"}

    if data.feedback in ("thumbs_up", "thumbs_down"):
        fb = UserFeedback(
            user_id=user_id,
            title_id=title.id,
            feedback_type=data.feedback,
        )
        db.add(fb)
    elif data.feedback == "save":
        item = UserWatchlistItem(
            user_id=user_id,
            title_id=title.id,
            status="saved",
        )
        db.add(item)
    elif data.feedback == "watched":
        entry = UserWatchHistory(
            user_id=user_id,
            title_id=title.id,
            source="manual",
        )
        db.add(entry)
        # Create pending rating reminder (if not already existing)
        existing = await db.execute(
            select(PendingRating).where(
                and_(
                    PendingRating.user_id == user_id,
                    PendingRating.tmdb_id == data.tmdb_id,
                )
            )
        )
        if not existing.scalar_one_or_none():
            db.add(PendingRating(
                user_id=user_id,
                title_id=title.id,
                tmdb_id=title.tmdb_id,
                media_type=title.media_type,
                title_name=title.title,
                poster_path=title.poster_path,
            ))

    await db.commit()
    return {"status": "ok"}
