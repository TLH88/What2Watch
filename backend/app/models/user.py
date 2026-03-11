from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    preferences: Mapped["UserPreferences | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    genre_preferences: Mapped[list["UserGenrePreference"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    feedback: Mapped[list["UserFeedback"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watch_history: Mapped[list["UserWatchHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watchlist: Mapped[list["UserWatchlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    pending_ratings: Mapped[list["PendingRating"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    hidden_gem_openness: Mapped[float] = mapped_column(Float, default=0.5)
    darkness_tolerance: Mapped[float] = mapped_column(Float, default=0.5)
    min_quality_threshold: Mapped[float] = mapped_column(Float, default=5.0)
    preferred_runtime_max: Mapped[int | None] = mapped_column(Integer)
    preferred_decades: Mapped[str | None] = mapped_column(String(255))  # comma-separated
    trakt_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    trakt_access_token: Mapped[str | None] = mapped_column(String(500))
    trakt_refresh_token: Mapped[str | None] = mapped_column(String(500))

    user: Mapped["User"] = relationship(back_populates="preferences")


class UserGenrePreference(Base):
    __tablename__ = "user_genre_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    genre_id: Mapped[int] = mapped_column(Integer)
    genre_name: Mapped[str] = mapped_column(String(100))
    preference: Mapped[str] = mapped_column(String(20))  # like | dislike | neutral

    user: Mapped["User"] = relationship(back_populates="genre_preferences")


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    feedback_type: Mapped[str] = mapped_column(String(20))  # thumbs_up | thumbs_down
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="feedback")


class UserWatchHistory(Base):
    __tablename__ = "user_watch_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(50))  # trakt | manual | jellyfin
    watched_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="watch_history")


class UserWatchlistItem(Base):
    __tablename__ = "user_watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="saved")  # saved | watching | watched
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="watchlist")


class PendingRating(Base):
    __tablename__ = "pending_ratings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    tmdb_id: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(10))
    title_name: Mapped[str] = mapped_column(String(500))
    poster_path: Mapped[str | None] = mapped_column(String(500))
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    rated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="pending_ratings")
