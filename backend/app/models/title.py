from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
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


class Title(Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    media_type: Mapped[str] = mapped_column(String(10))  # movie | tv
    title: Mapped[str] = mapped_column(String(500))
    original_title: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None] = mapped_column(Text)
    tagline: Mapped[str | None] = mapped_column(String(500))
    poster_path: Mapped[str | None] = mapped_column(String(255))
    backdrop_path: Mapped[str | None] = mapped_column(String(255))
    release_date: Mapped[datetime | None] = mapped_column(Date)
    runtime: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50))
    vote_average: Mapped[float | None] = mapped_column(Float)
    vote_count: Mapped[int | None] = mapped_column(Integer)
    popularity: Mapped[float | None] = mapped_column(Float)
    original_language: Mapped[str | None] = mapped_column(String(10))
    content_rating: Mapped[str | None] = mapped_column(String(20))

    # TV-specific
    number_of_seasons: Mapped[int | None] = mapped_column(Integer)
    number_of_episodes: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    genres: Mapped[list["TitleGenre"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    external_ids: Mapped[list["TitleExternalId"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    people: Mapped[list["TitlePerson"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    videos: Mapped[list["TitleVideo"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    watch_providers: Mapped[list["TitleWatchProvider"]] = relationship(back_populates="title", cascade="all, delete-orphan")
    local_availability: Mapped[list["TitleLocalAvailability"]] = relationship(back_populates="title", cascade="all, delete-orphan")


class TitleGenre(Base):
    __tablename__ = "title_genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    genre_id: Mapped[int] = mapped_column(Integer)
    genre_name: Mapped[str] = mapped_column(String(100))

    title: Mapped["Title"] = relationship(back_populates="genres")


class TitleExternalId(Base):
    __tablename__ = "title_external_ids"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(50))  # imdb | trakt | jellyfin | tvdb
    external_id: Mapped[str] = mapped_column(String(255))

    title: Mapped["Title"] = relationship(back_populates="external_ids")


class TitlePerson(Base):
    __tablename__ = "title_people"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    tmdb_person_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50))  # cast | director | writer
    character: Mapped[str | None] = mapped_column(String(255))
    order: Mapped[int | None] = mapped_column(Integer)
    profile_path: Mapped[str | None] = mapped_column(String(255))

    title: Mapped["Title"] = relationship(back_populates="people")


class TitleVideo(Base):
    __tablename__ = "title_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(255))
    site: Mapped[str] = mapped_column(String(50))  # YouTube
    video_type: Mapped[str] = mapped_column(String(50))  # Trailer | Teaser | Clip
    name: Mapped[str | None] = mapped_column(String(255))
    official: Mapped[bool] = mapped_column(Boolean, default=False)

    title: Mapped["Title"] = relationship(back_populates="videos")


class TitleWatchProvider(Base):
    __tablename__ = "title_watch_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[int] = mapped_column(Integer)
    provider_name: Mapped[str] = mapped_column(String(255))
    logo_path: Mapped[str | None] = mapped_column(String(255))
    provider_type: Mapped[str] = mapped_column(String(50))  # flatrate | rent | buy
    country: Mapped[str] = mapped_column(String(10), default="US")

    title: Mapped["Title"] = relationship(back_populates="watch_providers")


class TitleLocalAvailability(Base):
    __tablename__ = "title_local_availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(50))  # jellyfin
    source_item_id: Mapped[str] = mapped_column(String(255))
    library_name: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(Text)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    title: Mapped["Title"] = relationship(back_populates="local_availability")
