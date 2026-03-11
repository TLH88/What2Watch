import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.title import Title, TitleGenre, TitleLocalAvailability, TitleVideo
from app.models.user import UserFeedback, UserPreferences, UserWatchHistory
from app.schemas.discover import (
    ClarifyingQuestion,
    DiscoverResponse,
    ParsedQuery,
    RecommendationResult,
)
from app.services.integrations.tmdb import tmdb_client
from app.services.title_service import fetch_and_store_title

logger = logging.getLogger(__name__)

# In-memory session store (sufficient for household app)
_sessions: dict[str, dict] = {}

GENRE_MAP = {
    "action": 28, "adventure": 12, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 14, "history": 36, "horror": 27, "music": 10402,
    "mystery": 9648, "romance": 10749, "sci-fi": 878, "science fiction": 878,
    "thriller": 53, "war": 10752, "western": 37,
}

TV_GENRE_MAP = {
    "action": 10759, "adventure": 10759, "animation": 16, "comedy": 35,
    "crime": 80, "documentary": 99, "drama": 18, "family": 10751,
    "fantasy": 10765, "sci-fi": 10765, "science fiction": 10765,
    "mystery": 9648, "war": 10768, "western": 37, "kids": 10762,
    "romance": 10749, "thriller": 53, "horror": 27,
}

ERA_RANGES = {
    "classic": (None, 1979), "80s": (1980, 1989), "90s": (1990, 1999),
    "2000s": (2000, 2009), "2010s": (2010, 2019), "recent": (2020, None),
    "new": (2023, None), "old": (None, 1999),
}


def parse_query(query: str, media_type: str | None = None, genre_chips: list[str] | None = None) -> ParsedQuery:
    """Parse a free-text query into structured fields using keyword matching."""
    q = query.lower().strip()
    parsed = ParsedQuery(raw_query=query)

    # Media type
    if media_type:
        parsed.media_type = media_type
    elif "tv show" in q or "series" in q or "show" in q:
        parsed.media_type = "tv"
    elif "movie" in q or "film" in q:
        parsed.media_type = "movie"

    # Genres from chips
    if genre_chips:
        parsed.genres = [g.lower() for g in genre_chips]

    # Genres from text
    for genre in GENRE_MAP:
        if genre in q and genre not in parsed.genres:
            parsed.genres.append(genre)

    # Mood
    mood_keywords = {
        "feel-good": ["feel good", "feel-good", "uplifting", "happy", "heartwarming", "lighthearted"],
        "dark": ["dark", "gritty", "intense", "disturbing", "bleak"],
        "funny": ["funny", "hilarious", "laugh", "comedic"],
        "scary": ["scary", "terrifying", "creepy", "horror"],
        "thought-provoking": ["thought-provoking", "deep", "philosophical", "cerebral", "mind-bending"],
        "exciting": ["exciting", "thrilling", "edge of seat", "adrenaline"],
        "relaxing": ["relaxing", "chill", "easy", "casual", "light"],
        "emotional": ["emotional", "moving", "tearjerker", "cry"],
    }
    for mood, keywords in mood_keywords.items():
        if any(kw in q for kw in keywords):
            parsed.mood = mood
            break

    # Era
    for era, _ in ERA_RANGES.items():
        if era in q:
            parsed.era = era
            break
    if not parsed.era:
        for decade in ["1950", "1960", "1970", "1980", "1990", "2000", "2010", "2020"]:
            if decade in q:
                parsed.era = f"{decade[2:]}s"
                break

    # Runtime
    if any(w in q for w in ["short", "quick", "brief"]):
        parsed.runtime_pref = "short"
    elif any(w in q for w in ["long", "epic", "extended"]):
        parsed.runtime_pref = "long"

    # Quality
    if any(w in q for w in ["best", "top rated", "highly rated", "acclaimed", "masterpiece"]):
        parsed.quality_pref = "high"

    # Hidden gem
    if any(w in q for w in ["hidden gem", "underrated", "lesser known", "obscure", "overlooked"]):
        parsed.hidden_gem = True

    # Extract remaining keywords
    stop_words = {"a", "an", "the", "i", "me", "my", "want", "something", "like", "find",
                  "good", "really", "very", "that", "with", "for", "is", "to", "of", "and",
                  "in", "it", "on", "but", "or", "some", "about", "watch", "see", "looking"}
    words = q.split()
    parsed.keywords = [w for w in words if w not in stop_words and len(w) > 2
                       and w not in GENRE_MAP and w not in ERA_RANGES]

    return parsed


def get_clarifying_question(parsed: ParsedQuery) -> ClarifyingQuestion | None:
    """Return the single most useful clarifying question, or None if ready."""
    if not parsed.media_type:
        return ClarifyingQuestion(
            question="Are you looking for a movie or a TV show?",
            options=["Movie", "TV Show", "Either"],
            field="media_type",
        )
    if not parsed.genres and not parsed.mood and not parsed.keywords:
        return ClarifyingQuestion(
            question="What kind of mood or genre are you in the mood for?",
            options=["Action", "Comedy", "Drama", "Sci-Fi", "Thriller", "Horror", "Feel-Good", "Something Different"],
            field="genres",
        )
    return None


def apply_answer(parsed: ParsedQuery, field: str, answer: str) -> ParsedQuery:
    """Apply a clarifying answer to the parsed query."""
    a = answer.lower().strip()
    if field == "media_type":
        if "movie" in a:
            parsed.media_type = "movie"
        elif "tv" in a or "show" in a:
            parsed.media_type = "tv"
    elif field == "genres":
        if a == "something different":
            parsed.hidden_gem = True
        elif a == "feel-good":
            parsed.mood = "feel-good"
        else:
            parsed.genres.append(a)
    elif field == "mood":
        parsed.mood = a
    elif field == "era":
        parsed.era = a
    return parsed


async def generate_recommendations(
    db: AsyncSession, parsed: ParsedQuery, user_id: int
) -> list[RecommendationResult]:
    """Generate scored recommendations using TMDB discover + local data."""
    media_type = parsed.media_type or "movie"
    genre_map = TV_GENRE_MAP if media_type == "tv" else GENRE_MAP

    # Build TMDB discover params
    params: dict = {"sort_by": "vote_count.desc", "page": 1}

    # Genre filter
    genre_ids = []
    for g in parsed.genres:
        gid = genre_map.get(g)
        if gid:
            genre_ids.append(str(gid))
    if genre_ids:
        params["with_genres"] = ",".join(genre_ids)

    # Era filter
    if parsed.era and parsed.era in ERA_RANGES:
        start, end = ERA_RANGES[parsed.era]
        date_field = "first_air_date" if media_type == "tv" else "primary_release_date"
        if start:
            params[f"{date_field}.gte"] = f"{start}-01-01"
        if end:
            params[f"{date_field}.lte"] = f"{end}-12-31"

    # Quality filter
    if parsed.quality_pref == "high":
        params["vote_average.gte"] = 7.5
        params["vote_count.gte"] = 500

    # Runtime filter (movies only)
    if media_type == "movie" and parsed.runtime_pref:
        if parsed.runtime_pref == "short":
            params["with_runtime.lte"] = 100
        elif parsed.runtime_pref == "long":
            params["with_runtime.gte"] = 150

    # Hidden gem adjustments
    if parsed.hidden_gem:
        params["vote_count.gte"] = 50
        params["vote_count.lte"] = 1000
        params["vote_average.gte"] = 7.0
        params["sort_by"] = "vote_average.desc"

    # Fetch from TMDB
    try:
        if media_type == "tv":
            data = await tmdb_client.discover_tv(**params)
        else:
            data = await tmdb_client.discover_movies(**params)
    except Exception:
        logger.exception("TMDB discover call failed")
        return []

    # Load user context for scoring
    user_prefs = (await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )).scalar_one_or_none()

    watched_tmdb_ids = set()
    wh_result = await db.execute(
        select(Title.tmdb_id)
        .join(UserWatchHistory, UserWatchHistory.title_id == Title.id)
        .where(UserWatchHistory.user_id == user_id)
    )
    for row in wh_result:
        watched_tmdb_ids.add(row[0])

    disliked_tmdb_ids = set()
    fb_result = await db.execute(
        select(Title.tmdb_id)
        .join(UserFeedback, UserFeedback.title_id == Title.id)
        .where(UserFeedback.user_id == user_id, UserFeedback.feedback_type == "thumbs_down")
    )
    for row in fb_result:
        disliked_tmdb_ids.add(row[0])

    # Score and filter candidates
    candidates: list[RecommendationResult] = []
    for item in data.get("results", [])[:20]:
        tmdb_id = item["id"]

        # Hard filters
        if tmdb_id in watched_tmdb_ids:
            continue
        if tmdb_id in disliked_tmdb_ids:
            continue

        # Fetch and store full details
        try:
            title = await fetch_and_store_title(db, tmdb_id, media_type)
        except Exception:
            continue

        if not title:
            continue

        # Runtime hard filter
        if user_prefs and user_prefs.preferred_runtime_max and title.runtime:
            if title.runtime > user_prefs.preferred_runtime_max:
                continue

        # Check local availability
        locally_available = bool(title.local_availability)

        # Get trailer
        trailer_key = None
        for v in title.videos:
            if v.video_type == "Trailer" and v.site == "YouTube":
                trailer_key = v.key
                break

        # Score
        score = compute_score(title, parsed, user_prefs, locally_available)

        # Build genre list
        genre_names = [g.genre_name for g in title.genres]

        # Year
        year = str(title.release_date.year) if title.release_date else None

        # Explanation
        explanation = build_explanation(title, parsed, locally_available)

        candidates.append(RecommendationResult(
            tmdb_id=title.tmdb_id,
            media_type=title.media_type,
            title=title.title,
            year=year,
            overview=title.overview,
            poster_path=title.poster_path,
            vote_average=title.vote_average,
            content_rating=title.content_rating,
            runtime=title.runtime,
            genres=genre_names,
            explanation=explanation,
            score=score,
            is_hidden_gem=parsed.hidden_gem or (title.vote_count and title.vote_count < 500),
            locally_available=locally_available,
            trailer_key=trailer_key,
        ))

    # Sort by score descending
    candidates.sort(key=lambda r: r.score, reverse=True)

    # Return top 5 (3 best + up to 1 hidden gem + 1 curveball)
    return candidates[:5]


def compute_score(title, parsed: ParsedQuery, prefs, locally_available: bool) -> float:
    """Weighted scoring per the design plan."""
    score = 0.0

    # Quality composite (35%)
    if title.vote_average:
        score += (title.vote_average / 10.0) * 35

    # Genre/mood fit (25%)
    title_genres = {g.genre_name.lower() for g in title.genres}
    if parsed.genres:
        matches = sum(1 for g in parsed.genres if g in title_genres)
        score += (matches / max(len(parsed.genres), 1)) * 25
    elif parsed.mood:
        mood_genre_map = {
            "funny": {"comedy"}, "scary": {"horror"}, "exciting": {"action", "thriller"},
            "dark": {"thriller", "crime", "horror"}, "feel-good": {"comedy", "family", "romance"},
            "thought-provoking": {"drama", "science fiction"}, "emotional": {"drama", "romance"},
            "relaxing": {"comedy", "family", "animation"},
        }
        mood_genres = mood_genre_map.get(parsed.mood, set())
        if mood_genres & title_genres:
            score += 25

    # Freshness/diversity (15%)
    if title.popularity:
        if parsed.hidden_gem and title.popularity < 50:
            score += 15
        elif not parsed.hidden_gem and title.popularity > 20:
            score += min(title.popularity / 100 * 15, 15)

    # Local availability boost (10%)
    if locally_available:
        score += 10

    # Hidden gem bonus (10%)
    if title.vote_count and title.vote_count < 500 and title.vote_average and title.vote_average >= 7.0:
        score += 10

    # Recency bonus (5%)
    if title.release_date:
        years_old = (date.today().year - title.release_date.year)
        if years_old <= 2:
            score += 5
        elif years_old <= 5:
            score += 3

    return round(score, 1)


def build_explanation(title, parsed: ParsedQuery, locally_available: bool) -> str:
    """Build a short human-readable explanation for why this was recommended."""
    parts = []
    title_genres = [g.genre_name for g in title.genres[:3]]

    if title.vote_average and title.vote_average >= 8.0:
        parts.append(f"Highly rated ({title.vote_average:.1f}/10)")
    elif title.vote_average and title.vote_average >= 7.0:
        parts.append(f"Well reviewed ({title.vote_average:.1f}/10)")

    if parsed.genres:
        matching = [g for g in title_genres if g.lower() in parsed.genres]
        if matching:
            parts.append(f"Matches your {', '.join(matching).lower()} preference")

    if parsed.mood:
        parts.append(f"Fits your {parsed.mood} mood")

    if locally_available:
        parts.append("Available in your library")

    if title.vote_count and title.vote_count < 500:
        parts.append("Hidden gem")

    return ". ".join(parts) if parts else "Recommended based on your search"


async def start_discover(
    db: AsyncSession, user_id: int, query: str,
    media_type: str | None = None, genres: list[str] | None = None
) -> DiscoverResponse:
    session_id = str(uuid.uuid4())
    parsed = parse_query(query, media_type, genres)

    question = get_clarifying_question(parsed)
    if question:
        _sessions[session_id] = {"parsed": parsed, "user_id": user_id, "questions_asked": 1}
        return DiscoverResponse(session_id=session_id, status="asking", question=question)

    # Go straight to results
    results = await generate_recommendations(db, parsed, user_id)
    _sessions[session_id] = {"parsed": parsed, "user_id": user_id, "results": True}
    return DiscoverResponse(session_id=session_id, status="results", results=results)


async def respond_discover(
    db: AsyncSession, session_id: str, answer: str
) -> DiscoverResponse:
    session = _sessions.get(session_id)
    if not session:
        return DiscoverResponse(session_id=session_id, status="results", results=[])

    parsed: ParsedQuery = session["parsed"]
    user_id: int = session["user_id"]
    questions_asked: int = session.get("questions_asked", 0)

    # Apply the answer
    question = get_clarifying_question(parsed)
    if question:
        parsed = apply_answer(parsed, question.field, answer)
        session["parsed"] = parsed

    # Check if we need another question (max 3)
    if questions_asked < 3:
        next_question = get_clarifying_question(parsed)
        if next_question:
            session["questions_asked"] = questions_asked + 1
            return DiscoverResponse(session_id=session_id, status="asking", question=next_question)

    # Generate results
    results = await generate_recommendations(db, parsed, user_id)
    session["results"] = True
    return DiscoverResponse(session_id=session_id, status="results", results=results)
