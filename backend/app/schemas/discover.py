from __future__ import annotations

from pydantic import BaseModel


class DiscoverStartRequest(BaseModel):
    query: str
    media_type: str | None = None  # movie | tv | None (both)
    genres: list[str] = []
    include_watched: bool = True


class DiscoverRespondRequest(BaseModel):
    session_id: str
    answer: str


class DiscoverFeedbackRequest(BaseModel):
    tmdb_id: int
    feedback: str  # thumbs_up | thumbs_down | save | watched | not_interested


class ClarifyingQuestion(BaseModel):
    question: str
    options: list[str] = []
    field: str  # narrowing category (tone, era, subgenre, setting, style, format)


class AICandidate(BaseModel):
    """A candidate returned by the AI before TMDB resolution."""
    title: str
    year: int | None = None
    media_type: str = "movie"  # movie | tv
    confidence: float = 0.0
    relevance_reason: str = ""


class IntentResult(BaseModel):
    """Result of the AI intent detection + candidate generation call."""
    intent: str  # KNOWN_TITLE | TITLE_RECALL | RECOMMENDATION | SURPRISE_ME
    confidence: float = 0.0
    candidates: list[AICandidate] = []
    extracted_filters: dict = {}
    question: ClarifyingQuestion | None = None


class CollectionPart(BaseModel):
    tmdb_id: int
    title: str
    year: str | None = None
    poster_path: str | None = None
    overview: str | None = None


class CollectionInfo(BaseModel):
    collection_id: int
    name: str
    parts: list[CollectionPart] = []


class RecommendationResult(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    year: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    content_rating: str | None = None
    runtime: int | None = None
    genres: list[str] = []
    explanation: str = ""
    score: float = 0.0
    confidence: float = 0.0
    is_hidden_gem: bool = False
    is_curveball: bool = False
    locally_available: bool = False
    trailer_key: str | None = None
    collection: CollectionInfo | None = None


class DiscoverMoreRequest(BaseModel):
    session_id: str


class DiscoverResponse(BaseModel):
    session_id: str
    status: str  # asking | results
    question: ClarifyingQuestion | None = None
    results: list[RecommendationResult] = []
    has_more: bool = False
