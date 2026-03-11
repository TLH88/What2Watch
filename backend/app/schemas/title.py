from datetime import date, datetime

from pydantic import BaseModel


class TitleGenreOut(BaseModel):
    genre_id: int
    genre_name: str


class TitleExternalIdOut(BaseModel):
    source: str
    external_id: str


class TitlePersonOut(BaseModel):
    name: str
    role: str
    character: str | None = None
    order: int | None = None
    profile_path: str | None = None


class TitleVideoOut(BaseModel):
    key: str
    site: str
    video_type: str
    name: str | None = None
    official: bool = False


class TitleWatchProviderOut(BaseModel):
    provider_name: str
    logo_path: str | None = None
    provider_type: str
    country: str = "US"


class TitleLocalAvailabilityOut(BaseModel):
    source: str
    library_name: str | None = None
    available: bool = True


class TitleOut(BaseModel):
    id: int
    tmdb_id: int
    media_type: str
    title: str
    original_title: str | None = None
    overview: str | None = None
    tagline: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    release_date: date | None = None
    runtime: int | None = None
    status: str | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    popularity: float | None = None
    original_language: str | None = None
    content_rating: str | None = None
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    genres: list[TitleGenreOut] = []
    external_ids: list[TitleExternalIdOut] = []
    people: list[TitlePersonOut] = []
    videos: list[TitleVideoOut] = []
    watch_providers: list[TitleWatchProviderOut] = []
    local_availability: list[TitleLocalAvailabilityOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TitleSearchResult(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    overview: str | None = None
    poster_path: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    popularity: float | None = None


class TitleSearchResponse(BaseModel):
    results: list[TitleSearchResult]
    total_results: int
    total_pages: int
    page: int
