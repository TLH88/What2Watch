from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.user import (
    User,
    UserFeedback,
    UserGenrePreference,
    UserPreferences,
    UserWatchHistory,
    UserWatchlistItem,
)
from app.models.title import Title
from app.schemas.user import UserCreate, UserOut, UserProfileOut, UserUpdate
from app.services.integrations.trakt import sync_trakt_history, sync_trakt_ratings, trakt_client
from app.services.taste_profile import generate_taste_profile

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


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = (
            await db.execute(
                select(func.count(User.id)).where(
                    User.is_admin == True, User.is_active == True
                )
            )
        ).scalar()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400, detail="Cannot delete the last admin user"
            )

    await db.delete(user)
    await db.commit()


@router.post("/users/{user_id}/select", response_model=UserOut)
async def select_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


GENRE_ID_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37,
}


@router.put("/users/{user_id}/genre-preferences")
async def update_genre_preferences(
    user_id: int, data: dict, db: AsyncSession = Depends(get_db),
):
    """Replace all genre preferences for a user."""
    # Delete existing
    existing = await db.execute(
        select(UserGenrePreference).where(UserGenrePreference.user_id == user_id)
    )
    for gp in existing.scalars():
        await db.delete(gp)

    # Insert new
    for pref in data.get("preferences", []):
        genre_name = pref["genre_name"]
        genre_id = GENRE_ID_MAP.get(genre_name.lower(), 0)
        gp = UserGenrePreference(
            user_id=user_id,
            genre_id=genre_id,
            genre_name=genre_name,
            preference=pref["preference"],
        )
        db.add(gp)

    await db.commit()
    return {"status": "updated", "count": len(data.get("preferences", []))}


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

    # Count watch history by media type
    movies_watched = (
        await db.execute(
            select(func.count(UserWatchHistory.id))
            .join(Title, UserWatchHistory.title_id == Title.id)
            .where(UserWatchHistory.user_id == user_id, Title.media_type == "movie")
        )
    ).scalar()
    shows_watched = (
        await db.execute(
            select(func.count(UserWatchHistory.id))
            .join(Title, UserWatchHistory.title_id == Title.id)
            .where(UserWatchHistory.user_id == user_id, Title.media_type == "tv")
        )
    ).scalar()
    wl_count = (
        await db.execute(
            select(func.count(UserWatchlistItem.id)).where(
                UserWatchlistItem.user_id == user_id
            )
        )
    ).scalar()

    # Count feedback
    fb_count = (
        await db.execute(
            select(func.count(UserFeedback.id)).where(
                UserFeedback.user_id == user_id
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
        taste_profile=prefs.taste_profile if prefs else None,
        taste_profile_updated_at=prefs.taste_profile_updated_at.isoformat() if prefs and prefs.taste_profile_updated_at else None,
        genre_preferences=user.genre_preferences,
        movies_watched=movies_watched or 0,
        shows_watched=shows_watched or 0,
        watchlist_count=wl_count or 0,
        feedback_count=fb_count or 0,
    )


@router.post("/users/trakt/connect")
async def trakt_connect(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Start Trakt device code OAuth flow."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found")

    try:
        data = await trakt_client.get_device_code()
        return {
            "user_code": data["user_code"],
            "verification_url": data["verification_url"],
            "device_code": data["device_code"],
            "expires_in": data["expires_in"],
            "interval": data["interval"],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trakt API error: {e}")


@router.post("/users/trakt/poll")
async def trakt_poll(
    data: dict,
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Poll for Trakt device token after user authorizes."""
    device_code = data.get("device_code")
    if not device_code:
        raise HTTPException(status_code=400, detail="device_code required")

    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found")

    try:
        token_data = await trakt_client.poll_device_token(device_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Trakt API error: {e}")

    if "access_token" in token_data:
        prefs.trakt_access_token = token_data["access_token"]
        prefs.trakt_refresh_token = token_data.get("refresh_token")
        prefs.trakt_connected = True
        await db.commit()
        return {"status": "connected"}

    status = token_data.get("status", 0)
    if status == 400:
        return {"status": "pending"}
    if status == 404:
        return {"status": "expired"}
    if status == 409:
        return {"status": "already_used"}
    if status == 410:
        return {"status": "expired"}
    if status == 418:
        return {"status": "denied"}
    return {"status": "pending"}


@router.post("/users/trakt/disconnect")
async def trakt_disconnect(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect Trakt for a user."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found")

    prefs.trakt_access_token = None
    prefs.trakt_refresh_token = None
    prefs.trakt_connected = False
    await db.commit()
    return {"status": "disconnected"}


@router.post("/users/sync-trakt-history")
async def sync_history(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Import Trakt watch history."""
    count = await sync_trakt_history(db, user_id)
    return {"status": "ok", "imported": count}


@router.post("/users/sync-trakt-ratings")
async def sync_ratings(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Import Trakt ratings as feedback and auto-generate taste profile."""
    count = await sync_trakt_ratings(db, user_id)
    # Auto-generate taste profile after import
    profile = await generate_taste_profile(db, user_id)
    return {"status": "ok", "imported": count, "taste_profile": profile}


@router.post("/users/generate-taste-profile")
async def gen_taste_profile(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Generate or regenerate taste profile from existing feedback."""
    profile = await generate_taste_profile(db, user_id)
    return {"status": "ok", "taste_profile": profile}
