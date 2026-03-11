from pydantic import BaseModel


class RecallStartRequest(BaseModel):
    description: str


class RecallRespondRequest(BaseModel):
    session_id: str
    answer: str


class RecallConfirmRequest(BaseModel):
    session_id: str
    tmdb_id: int


class ExtractedClues(BaseModel):
    media_type: str | None = None
    era: str | None = None
    actors: list[str] = []
    setting: str | None = None
    country: str | None = None
    plot_details: list[str] = []
    tone: str | None = None
    is_animated: bool | None = None
    keywords: list[str] = []


class RecallCandidate(BaseModel):
    tmdb_id: int
    media_type: str
    title: str
    year: str | None = None
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    confidence: float = 0.0
    match_reasons: list[str] = []


class NarrowingQuestion(BaseModel):
    question: str
    options: list[str] = []
    field: str


class RecallResponse(BaseModel):
    session_id: str
    status: str  # asking | candidates | confirmed
    clues: ExtractedClues | None = None
    question: NarrowingQuestion | None = None
    candidates: list[RecallCandidate] = []
    confirmed_tmdb_id: int | None = None
