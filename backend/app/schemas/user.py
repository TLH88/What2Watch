from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    display_name: str
    avatar_url: str | None = None
    is_admin: bool = False


class UserUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    is_admin: bool | None = None
    onboarding_completed: bool | None = None


class UserOut(BaseModel):
    id: int
    display_name: str
    avatar_url: str | None = None
    is_admin: bool
    is_active: bool
    onboarding_completed: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserProfileOut(BaseModel):
    id: int
    display_name: str
    avatar_url: str | None = None
    is_admin: bool
    onboarding_completed: bool
    hidden_gem_openness: float = 0.5
    darkness_tolerance: float = 0.5
    min_quality_threshold: float = 5.0
    preferred_runtime_max: int | None = None
    trakt_connected: bool = False
    genre_preferences: list["GenrePreferenceOut"] = []
    watch_history_count: int = 0
    watchlist_count: int = 0


class GenrePreferenceOut(BaseModel):
    genre_id: int
    genre_name: str
    preference: str

    model_config = {"from_attributes": True}
