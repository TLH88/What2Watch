from pydantic import BaseModel


class DiscoverStartRequest(BaseModel):
    query: str
    media_type: str | None = None  # movie | tv | None (both)
    genres: list[str] = []


class DiscoverRespondRequest(BaseModel):
    session_id: str
    answer: str


class DiscoverFeedbackRequest(BaseModel):
    tmdb_id: int
    feedback: str  # thumbs_up | thumbs_down | save | watched | not_interested


class ParsedQuery(BaseModel):
    media_type: str | None = None
    genres: list[str] = []
    mood: str | None = None
    era: str | None = None
    runtime_pref: str | None = None  # short | medium | long
    quality_pref: str | None = None  # high | any
    hidden_gem: bool = False
    keywords: list[str] = []
    raw_query: str = ""


class ClarifyingQuestion(BaseModel):
    question: str
    options: list[str] = []
    field: str  # which ParsedQuery field this refines


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
    is_hidden_gem: bool = False
    locally_available: bool = False
    trailer_key: str | None = None


class DiscoverResponse(BaseModel):
    session_id: str
    status: str  # asking | results
    question: ClarifyingQuestion | None = None
    results: list[RecommendationResult] = []
