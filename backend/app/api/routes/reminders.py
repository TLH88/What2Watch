from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import PendingRating, UserFeedback

router = APIRouter()


@router.get("/reminders")
async def get_reminders(user_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """Get pending rating reminders for a user."""
    stmt = (
        select(PendingRating)
        .where(PendingRating.user_id == user_id)
        .where(PendingRating.dismissed == False)
        .where(PendingRating.rated == False)
        .order_by(PendingRating.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    reminders = result.scalars().all()
    return [
        {
            "id": r.id,
            "tmdb_id": r.tmdb_id,
            "media_type": r.media_type,
            "title": r.title_name,
            "poster_path": r.poster_path,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reminders
    ]


@router.post("/reminders/{reminder_id}/rate")
async def rate_reminder(
    reminder_id: int,
    feedback: str = Query(...),
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Rate a title from a pending reminder (thumbs_up or thumbs_down)."""
    stmt = select(PendingRating).where(PendingRating.id == reminder_id)
    result = await db.execute(stmt)
    reminder = result.scalar_one_or_none()
    if not reminder:
        return {"status": "not_found"}

    # Store the feedback using the title_id already on the reminder
    if feedback in ("thumbs_up", "thumbs_down"):
        db.add(UserFeedback(
            user_id=user_id,
            title_id=reminder.title_id,
            feedback_type=feedback,
        ))

    reminder.rated = True
    await db.commit()
    return {"status": "rated"}


@router.post("/reminders/{reminder_id}/dismiss")
async def dismiss_reminder(reminder_id: int, db: AsyncSession = Depends(get_db)):
    """Dismiss a pending rating reminder."""
    stmt = select(PendingRating).where(PendingRating.id == reminder_id)
    result = await db.execute(stmt)
    reminder = result.scalar_one_or_none()
    if not reminder:
        return {"status": "not_found"}

    reminder.dismissed = True
    await db.commit()
    return {"status": "dismissed"}
