from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.title import Title
from app.models.user import PendingRating, UserWatchHistory
from app.schemas.recall import (
    RecallConfirmRequest,
    RecallRespondRequest,
    RecallResponse,
    RecallStartRequest,
)
from app.services.recall_service import respond_recall, start_recall

router = APIRouter()


@router.post("/recall/start", response_model=RecallResponse)
async def recall_start(data: RecallStartRequest):
    return await start_recall(data.description)


@router.post("/recall/respond", response_model=RecallResponse)
async def recall_respond(data: RecallRespondRequest):
    return await respond_recall(data.session_id, data.answer)


@router.post("/recall/confirm")
async def recall_confirm(
    data: RecallConfirmRequest,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a recalled title — add to watch history and create pending rating."""
    result = await db.execute(
        select(Title).where(Title.tmdb_id == data.tmdb_id)
    )
    title = result.scalar_one_or_none()
    if not title:
        return {"status": "title_not_found", "tmdb_id": data.tmdb_id}

    # Check if already in watch history
    existing = await db.execute(
        select(UserWatchHistory).where(
            UserWatchHistory.user_id == user_id,
            UserWatchHistory.title_id == title.id,
        )
    )
    if not existing.scalar_one_or_none():
        entry = UserWatchHistory(
            user_id=user_id,
            title_id=title.id,
            source="recall",
        )
        db.add(entry)

        # Create pending rating reminder
        existing_rating = await db.execute(
            select(PendingRating).where(
                PendingRating.user_id == user_id,
                PendingRating.title_id == title.id,
            )
        )
        if not existing_rating.scalar_one_or_none():
            rating = PendingRating(
                user_id=user_id,
                title_id=title.id,
                tmdb_id=title.tmdb_id,
                media_type=title.media_type,
                title_name=title.title,
            )
            db.add(rating)

        await db.commit()

    return {"status": "confirmed", "tmdb_id": data.tmdb_id}
