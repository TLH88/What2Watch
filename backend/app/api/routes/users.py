from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import (
    User,
    UserGenrePreference,
    UserPreferences,
    UserWatchHistory,
    UserWatchlistItem,
)
from app.schemas.user import UserCreate, UserOut, UserProfileOut, UserUpdate

router = APIRouter()


@router.get("/users", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.is_active == True).order_by(User.created_at)
    )
    return result.scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Enforce max 4 regular users + 1 admin (5 total)
    count_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    count = count_result.scalar()
    if count >= 5:
        raise HTTPException(status_code=400, detail="Maximum of 5 users reached")

    user = User(
        display_name=data.display_name,
        avatar_url=data.avatar_url,
        is_admin=data.is_admin,
    )
    db.add(user)
    await db.flush()

    # Create default preferences
    prefs = UserPreferences(user_id=user.id)
    db.add(prefs)

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/select", response_model=UserOut)
async def select_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/profile", response_model=UserProfileOut)
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.preferences),
            selectinload(User.genre_preferences),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Count watch history and watchlist
    wh_count = (
        await db.execute(
            select(func.count(UserWatchHistory.id)).where(
                UserWatchHistory.user_id == user_id
            )
        )
    ).scalar()
    wl_count = (
        await db.execute(
            select(func.count(UserWatchlistItem.id)).where(
                UserWatchlistItem.user_id == user_id
            )
        )
    ).scalar()

    prefs = user.preferences
    return UserProfileOut(
        id=user.id,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_admin=user.is_admin,
        onboarding_completed=user.onboarding_completed,
        hidden_gem_openness=prefs.hidden_gem_openness if prefs else 0.5,
        darkness_tolerance=prefs.darkness_tolerance if prefs else 0.5,
        min_quality_threshold=prefs.min_quality_threshold if prefs else 5.0,
        preferred_runtime_max=prefs.preferred_runtime_max if prefs else None,
        trakt_connected=prefs.trakt_connected if prefs else False,
        genre_preferences=user.genre_preferences,
        watch_history_count=wh_count,
        watchlist_count=wl_count,
    )
