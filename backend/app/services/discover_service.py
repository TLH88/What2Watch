import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.title import Title, TitleGenre, TitleLocalAvailability, TitleVideo
from app.models.user import LanguagePreference, UserFeedback, UserGenrePreference, UserPreferences, UserWatchHistory
from app.schemas.discover import (
    AICandidate,
    ClarifyingQuestion,
    CollectionInfo,
    CollectionPart,
    DiscoverResponse,
    IntentResult,
    RecommendationResult,
)
from app.services.ai import get_ai_provider, parse_ai_json
from app.services.ai.prompts import (
    INTENT_AND_CANDIDATES_SYSTEM,
    INTENT_AND_CANDIDATES_USER,
    NARROW_CANDIDATES_SYSTEM,
    NARROW_CANDIDATES_USER,
)
from app.services.integrations.tmdb import tmdb_client
from app.services.title_service import fetch_and_store_title

logger = logging.getLogger(__name__)

# In-memory session store (sufficient for household app)
_sessions: dict[str, dict] = {}

# Max narrowing rounds before forcing results
MAX_NARROWING_ROUNDS = 3

# Target candidate count — narrowing stops when at or below this
TARGET_CANDIDATES = 25

# TMDB genre ID maps (used by curveball logic)
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


# ---------------------------------------------------------------------------
# User context loading
# ---------------------------------------------------------------------------

async def _load_user_context(db: AsyncSession, user_id: int):
    """Load user preferences, watch history, disliked titles, and genre preferences."""
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

    # Genre preferences
    genre_prefs: dict[str, str] = {}  # genre_name -> "like" | "dislike"
    gp_result = await db.execute(
        select(UserGenrePreference).where(UserGenrePreference.user_id == user_id)
    )
    for gp in gp_result.scalars():
        genre_prefs[gp.genre_name.lower()] = gp.preference

    # Language preferences (system-wide, not per-user)
    lang_result = await db.execute(
        select(LanguagePreference.language_code).order_by(LanguagePreference.priority)
    )
    preferred_langs = {row[0] for row in lang_result}

    return user_prefs, watched_tmdb_ids, disliked_tmdb_ids, genre_prefs, preferred_langs


# ---------------------------------------------------------------------------
# AI: Intent detection + candidate generation
# ---------------------------------------------------------------------------

async def _ai_generate_candidates(
    query: str,
    genres: list[str],
    language_prefs: set[str],
    media_type: str | None,
    taste_profile: str,
) -> IntentResult | None:
    """Call AI for intent detection + up to 100 candidates."""
    provider = get_ai_provider()
    if not provider:
        logger.warning("No AI provider available for candidate generation")
        return None

    user_msg = INTENT_AND_CANDIDATES_USER.format(
        query=query,
        genres=", ".join(genres) if genres else "none specified",
        languages=", ".join(language_prefs) if language_prefs else "any",
        media_type=media_type or "any (movie or tv)",
        taste_profile=taste_profile or "not yet available",
    )

    response = await provider.chat(INTENT_AND_CANDIDATES_SYSTEM, user_msg)
    data = parse_ai_json(response)
    if not data or not isinstance(data, dict):
        logger.error("Failed to parse AI intent response")
        return None

    intent = data.get("intent", "RECOMMENDATION")
    candidates = []
    for c in data.get("candidates", []):
        if isinstance(c, dict) and c.get("title"):
            candidates.append(AICandidate(
                title=c["title"],
                year=c.get("year"),
                media_type=c.get("media_type", "movie"),
                confidence=c.get("confidence", 0.5),
                relevance_reason=c.get("relevance_reason", ""),
            ))

    # Build narrowing question if AI provided one
    question = None
    if data.get("narrowing_question"):
        question = ClarifyingQuestion(
            question=data["narrowing_question"],
            options=data.get("narrowing_options", []),
            field=data.get("narrowing_field", "general"),
        )

    result = IntentResult(
        intent=intent,
        confidence=data.get("confidence", 0.5),
        candidates=candidates,
        extracted_filters=data.get("extracted_filters", {}),
        question=question,
    )

    logger.info(
        "AI intent=%s, confidence=%.2f, candidates=%d, has_question=%s",
        result.intent, result.confidence, len(result.candidates), result.question is not None,
    )
    # Log top candidates for debugging
    for c in result.candidates[:10]:
        logger.info("  Candidate: %s (%s, %s) confidence=%.2f — %s", c.title, c.year, c.media_type, c.confidence, c.relevance_reason[:80])
    return result


# ---------------------------------------------------------------------------
# AI: Narrow candidates based on user answer
# ---------------------------------------------------------------------------

async def _ai_narrow_candidates(
    candidates: list[dict],
    user_answer: str,
    original_query: str,
    question_text: str,
    asked_questions: list[str],
) -> dict | None:
    """Call AI to filter candidates by user answer + add up to 10 new."""
    provider = get_ai_provider()
    if not provider:
        return None

    # Format candidates for the prompt
    candidate_text = "\n".join(
        f"- {c['title']} ({c.get('year', '?')}) [{c.get('media_type', 'movie')}] "
        f"confidence={c.get('confidence', 0.5):.2f} — {c.get('relevance_reason', '')}"
        for c in candidates
    )

    user_msg = NARROW_CANDIDATES_USER.format(
        query=original_query,
        question=question_text,
        answer=user_answer,
        asked_questions=", ".join(asked_questions) if asked_questions else "none",
        count=len(candidates),
        candidates=candidate_text,
    )

    response = await provider.chat(NARROW_CANDIDATES_SYSTEM, user_msg)
    data = parse_ai_json(response)
    if not data or not isinstance(data, dict):
        logger.error("Failed to parse AI narrowing response")
        return None

    logger.info(
        "AI narrowing: %d candidates returned, has_question=%s",
        len(data.get("candidates", [])),
        data.get("narrowing_question") is not None,
    )
    return data


# ---------------------------------------------------------------------------
# TMDB resolution: convert AI candidates to real TMDB entries
# ---------------------------------------------------------------------------

async def _resolve_single_candidate(
    db: AsyncSession,
    candidate: dict,
) -> tuple[dict, Title | None]:
    """Resolve a single AI candidate to a TMDB Title. Returns (candidate, title_or_none)."""
    title_str = candidate["title"]
    year = candidate.get("year")
    media_type = candidate.get("media_type", "movie")

    # Strategy 1: Search by title + year
    search_fn = tmdb_client.search_movie if media_type == "movie" else tmdb_client.search_tv
    try:
        results = await search_fn(title_str, year=year)
        if not results.get("results"):
            # Strategy 2: Search without year
            results = await search_fn(title_str)
        if not results.get("results"):
            # Strategy 3: Multi-search fallback
            results = await tmdb_client.search_multi(title_str)
    except Exception:
        logger.exception("TMDB search failed for '%s'", title_str)
        return candidate, None

    tmdb_results = results.get("results", [])
    if not tmdb_results:
        logger.debug("No TMDB match for '%s' (%s)", title_str, year)
        return candidate, None

    # Pick best match — prefer exact year match if available
    best = tmdb_results[0]
    if year:
        for r in tmdb_results:
            r_date = r.get("release_date") or r.get("first_air_date") or ""
            if r_date.startswith(str(year)):
                best = r
                break

    tmdb_id = best["id"]
    # Determine actual media_type from result
    actual_type = best.get("media_type", media_type)
    if actual_type not in ("movie", "tv"):
        actual_type = media_type

    try:
        title = await fetch_and_store_title(db, tmdb_id, actual_type)
        return candidate, title
    except Exception:
        logger.warning("fetch_and_store_title failed for tmdb_id=%s, attempting rollback + lookup", tmdb_id)
        try:
            await db.rollback()
            # Title may already exist — try to fetch it directly
            from app.services.title_service import get_title_by_tmdb_id
            title = await get_title_by_tmdb_id(db, tmdb_id)
            if title:
                return candidate, title
        except Exception:
            logger.exception("Rollback/lookup also failed for tmdb_id=%s", tmdb_id)
        return candidate, None


async def _resolve_via_tmdb(
    db: AsyncSession,
    candidates: list[dict],
    watched_ids: set[int],
    disliked_ids: set[int],
    include_watched: bool,
    language_prefs: set[str] | None = None,
    media_type: str | None = None,
) -> list[RecommendationResult]:
    """Resolve AI candidates to TMDB entries with parallel lookups.

    Filters out watched titles (unless include_watched), disliked titles,
    titles not matching language preferences, and titles not matching
    the requested media_type.
    Returns RecommendationResult list sorted by confidence.
    """
    resolved: list[RecommendationResult] = []
    seen_ids: set[int] = set()

    # Process candidates sequentially to avoid shared-session issues
    # (asyncio.gather with a shared db session causes MissingGreenlet
    # when one coroutine's commit expires another's ORM objects)
    for candidate in candidates:
        try:
            candidate_data, title = await _resolve_single_candidate(db, candidate)
        except Exception as e:
            logger.error("Resolution error: %s", e)
            continue

        if title is None:
            continue

        # Dedup
        if title.tmdb_id in seen_ids:
            continue
        seen_ids.add(title.tmdb_id)

        # Dislike filter
        if title.tmdb_id in disliked_ids:
            continue

        # Language filter
        if language_prefs and title.original_language:
            if title.original_language not in language_prefs:
                continue

        # Media type filter
        if media_type and title.media_type != media_type:
            continue

        # Build result
        rec = await _build_recommendation_result(db, title, candidate_data)

        # Watch filter
        if not include_watched and title.tmdb_id in watched_ids:
            continue

        resolved.append(rec)

    # Sort by confidence descending
    resolved.sort(key=lambda r: r.confidence, reverse=True)
    return resolved


async def _build_recommendation_result(
    db: AsyncSession,
    title: Title,
    candidate: dict,
) -> RecommendationResult:
    """Build a RecommendationResult from a Title and AI candidate data."""
    # Load genres
    genre_result = await db.execute(
        select(TitleGenre.genre_name).where(TitleGenre.title_id == title.id)
    )
    genres = [row[0] for row in genre_result]

    # Check local availability
    local_result = await db.execute(
        select(TitleLocalAvailability).where(TitleLocalAvailability.title_id == title.id)
    )
    locally_available = local_result.scalar_one_or_none() is not None

    # Get trailer
    trailer_key = None
    video_result = await db.execute(
        select(TitleVideo.key).where(
            TitleVideo.title_id == title.id,
            TitleVideo.site == "YouTube",
            TitleVideo.video_type.in_(["Trailer", "Teaser"]),
        ).order_by(TitleVideo.video_type)  # Trailer before Teaser
    )
    trailer_row = video_result.first()
    if trailer_row:
        trailer_key = trailer_row[0]

    confidence = candidate.get("confidence", 0.0)
    explanation = candidate.get("relevance_reason", "")

    return RecommendationResult(
        tmdb_id=title.tmdb_id,
        media_type=title.media_type,
        title=title.title,
        year=str(title.release_date.year) if title.release_date else None,
        overview=title.overview,
        poster_path=title.poster_path,
        vote_average=title.vote_average,
        content_rating=title.content_rating,
        runtime=title.runtime,
        genres=genres,
        explanation=explanation,
        score=confidence * 100,  # backward compat: score as 0-100
        confidence=confidence,
        is_hidden_gem=False,
        is_curveball=False,
        locally_available=locally_available,
        trailer_key=trailer_key,
    )


# ---------------------------------------------------------------------------
# Hidden gem selection
# ---------------------------------------------------------------------------

def _select_hidden_gem(
    resolved: list[RecommendationResult],
    top_ids: set[int],
) -> RecommendationResult | None:
    """Pick hidden gem: highest vote_average from remaining candidates with rating >= 7.0."""
    for r in resolved:
        if r.tmdb_id not in top_ids and r.vote_average and r.vote_average >= 7.0:
            r.is_hidden_gem = True
            r.explanation = f"Hidden gem — rated {r.vote_average:.1f}/10. {r.explanation}"
            return r
    # Fallback: pick any remaining candidate not in top results
    for r in resolved:
        if r.tmdb_id not in top_ids:
            r.is_hidden_gem = True
            r.explanation = f"Hidden gem — {r.explanation}"
            return r
    return None


async def _ai_suggest_hidden_gem(
    db: AsyncSession,
    query: str,
    genres: list[str],
    exclude_ids: set[int],
    watched_ids: set[int],
    disliked_ids: set[int],
    language_prefs: set[str] | None = None,
) -> RecommendationResult | None:
    """Ask AI for a hidden gem when normal selection has no candidates."""
    provider = get_ai_provider()
    if not provider:
        return None

    genre_hint = f" in the {', '.join(genres)} genre(s)" if genres else ""
    prompt = (
        f'The user searched for: "{query}"{genre_hint}. '
        f"Suggest ONE lesser-known but highly rated movie or TV show that fits this theme. "
        f"It should be something most people haven't seen but is critically acclaimed or has a cult following. "
        f"Respond with JSON only: "
        f'{{"title": "Title", "year": 2020, "media_type": "movie", "confidence": 0.6, '
        f'"relevance_reason": "Why this is a hidden gem"}}'
    )

    try:
        response = await provider.chat(
            "You are a movie expert specializing in lesser-known films and TV shows. Respond with JSON only.",
            prompt,
        )
        data = parse_ai_json(response)
        if not data or not data.get("title"):
            return None

        title_str = data["title"]
        year = data.get("year")
        mtype = data.get("media_type", "movie")

        # Search TMDB
        if mtype == "tv":
            search_results = await tmdb_client.search_tv(title_str, year=year)
        else:
            search_results = await tmdb_client.search_movie(title_str, year=year)

        for item in search_results.get("results", [])[:3]:
            tmdb_id = item["id"]
            if tmdb_id in exclude_ids or tmdb_id in watched_ids or tmdb_id in disliked_ids:
                continue
            try:
                title = await fetch_and_store_title(db, tmdb_id, mtype)
                if language_prefs and title.original_language and title.original_language not in language_prefs:
                    continue
                rec = await _build_recommendation_result(db, title, data)
                rec.is_hidden_gem = True
                rec.explanation = f"Hidden gem — {data.get('relevance_reason', 'A lesser-known gem')}"
                return rec
            except Exception:
                continue
    except Exception:
        logger.exception("AI hidden gem suggestion failed")

    return None


# ---------------------------------------------------------------------------
# Curveball: independent TMDB discover search
# ---------------------------------------------------------------------------

async def _find_curveball(
    db: AsyncSession,
    query: str,
    genres: list[str],
    media_type: str | None,
    exclude_ids: set[int],
    watched_ids: set[int],
    disliked_ids: set[int],
    language_prefs: set[str] | None = None,
) -> RecommendationResult | None:
    """Find a curveball recommendation. Tries multiple strategies:
    1. TMDB genre-based discover
    2. TMDB keyword search
    3. AI-suggested curveball (guaranteed fallback)
    """
    target_type = media_type or "movie"

    # Strategy 1: Genre-based TMDB discover
    if genres:
        genre_name = genres[0].lower()
        genre_map = GENRE_MAP if target_type == "movie" else TV_GENRE_MAP
        genre_id = genre_map.get(genre_name)
        if genre_id:
            try:
                discover_fn = tmdb_client.discover_movies if target_type == "movie" else tmdb_client.discover_tv
                results = await discover_fn(with_genres=str(genre_id), sort_by="vote_average.desc", vote_count_gte=100)
                for item in results.get("results", [])[:15]:
                    tmdb_id = item["id"]
                    if tmdb_id in exclude_ids or tmdb_id in watched_ids or tmdb_id in disliked_ids:
                        continue
                    try:
                        title = await fetch_and_store_title(db, tmdb_id, target_type)
                        if language_prefs and title.original_language and title.original_language not in language_prefs:
                            continue
                        rec = await _build_recommendation_result(db, title, {
                            "confidence": 0.3,
                            "relevance_reason": f"A different take on {genre_name}",
                        })
                        rec.is_curveball = True
                        rec.explanation = f"Curveball — a different take on {genre_name}"
                        return rec
                    except Exception:
                        continue
            except Exception:
                logger.exception("Curveball genre discover failed")

    # Strategy 2: Keyword search from user query
    words = [w for w in query.lower().split() if len(w) > 3]
    for word in words[:3]:
        try:
            search_results = await tmdb_client.search_multi(word)
            for item in search_results.get("results", [])[:10]:
                item_type = item.get("media_type")
                if item_type not in ("movie", "tv"):
                    continue
                tmdb_id = item["id"]
                if tmdb_id in exclude_ids or tmdb_id in watched_ids or tmdb_id in disliked_ids:
                    continue
                try:
                    title = await fetch_and_store_title(db, tmdb_id, item_type)
                    if language_prefs and title.original_language and title.original_language not in language_prefs:
                        continue
                    rec = await _build_recommendation_result(db, title, {
                        "confidence": 0.3,
                        "relevance_reason": f"A different take based on '{word}'",
                    })
                    rec.is_curveball = True
                    rec.explanation = f"Curveball — a different take based on '{word}'"
                    return rec
                except Exception:
                    continue
        except Exception:
            continue

    # Strategy 3: AI-suggested curveball (guaranteed fallback)
    provider = get_ai_provider()
    if provider:
        genre_hint = f" in the {', '.join(genres)} genre(s)" if genres else ""
        prompt = (
            f'The user searched for: "{query}"{genre_hint}. '
            f"Suggest ONE movie or TV show that is an unexpected, creative curveball recommendation. "
            f"It should be tangentially related but from a different angle — a different genre, era, or style "
            f"that shares a thematic connection. "
            f"Respond with JSON only: "
            f'{{"title": "Title", "year": 2020, "media_type": "movie", "confidence": 0.3, '
            f'"relevance_reason": "Why this is an unexpected but interesting pick"}}'
        )
        try:
            response = await provider.chat(
                "You are a creative movie recommender who loves surprising people with unexpected picks. Respond with JSON only.",
                prompt,
            )
            data = parse_ai_json(response)
            if data and data.get("title"):
                title_str = data["title"]
                year = data.get("year")
                mtype = data.get("media_type", "movie")
                if mtype == "tv":
                    search_results = await tmdb_client.search_tv(title_str, year=year)
                else:
                    search_results = await tmdb_client.search_movie(title_str, year=year)
                for item in search_results.get("results", [])[:3]:
                    tmdb_id = item["id"]
                    if tmdb_id in exclude_ids or tmdb_id in watched_ids or tmdb_id in disliked_ids:
                        continue
                    try:
                        title = await fetch_and_store_title(db, tmdb_id, mtype)
                        if language_prefs and title.original_language and title.original_language not in language_prefs:
                            continue
                        rec = await _build_recommendation_result(db, title, data)
                        rec.is_curveball = True
                        rec.explanation = f"Curveball — {data.get('relevance_reason', 'An unexpected pick')}"
                        return rec
                    except Exception:
                        continue
        except Exception:
            logger.exception("AI curveball suggestion failed")

    return None


# ---------------------------------------------------------------------------
# Final assembly: top 5 + hidden gem + curveball
# ---------------------------------------------------------------------------

async def _assemble_final(
    db: AsyncSession,
    resolved: list[RecommendationResult],
    query: str,
    genres: list[str],
    media_type: str | None,
    user_id: int,
    watched_ids: set[int],
    disliked_ids: set[int],
    language_prefs: set[str] | None = None,
) -> list[RecommendationResult]:
    """Assemble final 12 results: top 10 + hidden gem + curveball.

    Hidden gem and curveball are MANDATORY — each has multiple fallback
    strategies to guarantee they always appear.
    """

    # Top 10
    top_10 = resolved[:10]
    top_ids = {r.tmdb_id for r in top_10}

    final = list(top_10)

    # Hidden gem from positions 11-30
    remaining = resolved[10:30]
    hidden_gem = _select_hidden_gem(remaining, top_ids)

    # Hidden gem fallback: ask AI for a suggestion
    if not hidden_gem:
        hidden_gem = await _ai_suggest_hidden_gem(
            db, query, genres, top_ids, watched_ids, disliked_ids, language_prefs,
        )

    if hidden_gem:
        top_ids.add(hidden_gem.tmdb_id)
        final.append(hidden_gem)

    # Curveball (has 3-strategy fallback internally)
    curveball = await _find_curveball(
        db, query, genres, media_type,
        exclude_ids=top_ids,
        watched_ids=watched_ids,
        disliked_ids=disliked_ids,
        language_prefs=language_prefs,
    )
    if curveball:
        final.append(curveball)

    return final


# ---------------------------------------------------------------------------
# Collection enrichment (on-demand from TMDB, not persisted)
# ---------------------------------------------------------------------------

async def _enrich_collections(results: list[RecommendationResult]) -> None:
    """Fetch TMDB collection data for movie results that belong to a collection."""
    for rec in results:
        if rec.media_type != "movie":
            continue
        try:
            movie_data = await tmdb_client.get_movie(rec.tmdb_id)
            btc = movie_data.get("belongs_to_collection")
            if not btc:
                continue
            collection_data = await tmdb_client.get_collection(btc["id"])
            parts = []
            for part in sorted(
                collection_data.get("parts", []),
                key=lambda p: p.get("release_date") or "",
            ):
                rd = part.get("release_date") or ""
                parts.append(CollectionPart(
                    tmdb_id=part["id"],
                    title=part.get("title", ""),
                    year=rd[:4] if len(rd) >= 4 else None,
                    poster_path=part.get("poster_path"),
                    overview=part.get("overview"),
                ))
            rec.collection = CollectionInfo(
                collection_id=btc["id"],
                name=btc.get("name", ""),
                parts=parts,
            )
        except Exception:
            logger.debug("Collection fetch failed for tmdb_id=%s", rec.tmdb_id)


# ---------------------------------------------------------------------------
# Entry point: start discover
# ---------------------------------------------------------------------------

async def start_discover(
    db: AsyncSession,
    user_id: int,
    query: str,
    media_type: str | None = None,
    genres: list[str] | None = None,
    include_watched: bool = False,
) -> DiscoverResponse:
    """Start a new discover session. AI determines intent and generates candidates."""
    session_id = str(uuid.uuid4())
    genres = genres or []

    # Load user context
    user_prefs, watched_ids, disliked_ids, genre_prefs, preferred_langs = await _load_user_context(db, user_id)

    # Call AI for intent detection + candidates
    intent_result = await _ai_generate_candidates(
        query=query,
        genres=genres,
        language_prefs=preferred_langs,
        media_type=media_type,
        taste_profile=user_prefs.taste_profile if user_prefs else ""
    )

    if not intent_result or not intent_result.candidates:
        logger.warning("AI returned no candidates for query: %s", query)
        return DiscoverResponse(session_id=session_id, status="results", results=[])

    # Convert candidates to dicts for session storage
    candidate_dicts = [c.model_dump() for c in intent_result.candidates]

    # Merge AI-extracted genres into working genres list
    extracted_genres = intent_result.extracted_filters.get("genres", [])
    for g in extracted_genres:
        if g.lower() not in [x.lower() for x in genres]:
            genres.append(g)

    # Store session
    _sessions[session_id] = {
        "user_id": user_id,
        "query": query,
        "media_type": media_type,
        "genres": genres,
        "include_watched": include_watched,
        "intent": intent_result.intent,
        "candidates": candidate_dicts,
        "narrowing_round": 0,
        "asked_questions": [],
        "language_prefs": preferred_langs,
        "watched_ids": watched_ids,
        "disliked_ids": disliked_ids,
    }

    # KNOWN_TITLE and TITLE_RECALL: resolve immediately
    # KNOWN_TITLE: single result, no hidden gem or curveball
    if intent_result.intent == "KNOWN_TITLE":
        resolved = await _resolve_via_tmdb(
            db, candidate_dicts, watched_ids, disliked_ids,
            include_watched=True,  # always show for title lookups
            language_prefs=None,  # no language filter for direct lookups
        )
        await _enrich_collections(resolved)
        return DiscoverResponse(session_id=session_id, status="results", results=resolved)

    # TITLE_RECALL / RECOMMENDATION / SURPRISE_ME: full assembly with hidden gem + curveball
    candidate_count = len(candidate_dicts)
    logger.info("Candidate count after AI generation: %d", candidate_count)

    if candidate_count > TARGET_CANDIDATES and intent_result.question:
        # Ask narrowing question
        _sessions[session_id]["asked_questions"].append(intent_result.question.question)
        return DiscoverResponse(
            session_id=session_id,
            status="asking",
            question=intent_result.question,
        )

    # Resolve and assemble final results
    resolved = await _resolve_via_tmdb(
        db, candidate_dicts, watched_ids, disliked_ids,
        include_watched, preferred_langs, media_type,
    )
    final = await _assemble_final(
        db, resolved, query, genres, media_type, user_id,
        watched_ids, disliked_ids, preferred_langs,
    )
    await _enrich_collections(final)

    # Store all resolved results (excluding special picks) for "load more"
    final_ids = {r.tmdb_id for r in final}
    remaining = [r for r in resolved if r.tmdb_id not in final_ids]
    _sessions[session_id]["all_remaining"] = [r.model_dump() for r in remaining]
    _sessions[session_id]["more_offset"] = 0

    has_more = len(remaining) > 0
    return DiscoverResponse(session_id=session_id, status="results", results=final, has_more=has_more)


# ---------------------------------------------------------------------------
# Entry point: load more results from an existing session
# ---------------------------------------------------------------------------

LOAD_MORE_PAGE_SIZE = 10


async def load_more_discover(
    db: AsyncSession,
    session_id: str,
) -> DiscoverResponse:
    """Return the next batch of results from a completed discover session."""
    session = _sessions.get(session_id)
    if not session:
        logger.error("Session not found for load_more: %s", session_id)
        return DiscoverResponse(session_id=session_id, status="results", results=[])

    all_remaining = session.get("all_remaining", [])
    offset = session.get("more_offset", 0)

    # Slice next page
    page = all_remaining[offset : offset + LOAD_MORE_PAGE_SIZE]
    next_offset = offset + LOAD_MORE_PAGE_SIZE
    session["more_offset"] = next_offset

    # Convert dicts back to RecommendationResult
    results = [RecommendationResult(**r) for r in page]
    await _enrich_collections(results)

    has_more = next_offset < len(all_remaining)
    return DiscoverResponse(
        session_id=session_id,
        status="results",
        results=results,
        has_more=has_more,
    )


# ---------------------------------------------------------------------------
# Entry point: respond to narrowing question
# ---------------------------------------------------------------------------

async def respond_discover(
    db: AsyncSession,
    session_id: str,
    answer: str,
) -> DiscoverResponse:
    """Handle user's answer to a narrowing question."""
    session = _sessions.get(session_id)
    if not session:
        logger.error("Session not found: %s", session_id)
        return DiscoverResponse(session_id=session_id, status="results", results=[])

    user_id = session["user_id"]
    query = session["query"]
    candidates = session["candidates"]
    asked_questions = session["asked_questions"]
    narrowing_round = session["narrowing_round"] + 1
    include_watched = session["include_watched"]
    watched_ids = session["watched_ids"]
    disliked_ids = session["disliked_ids"]
    language_prefs = session["language_prefs"]
    genres = session["genres"]
    media_type = session["media_type"]

    # Get the last asked question text
    last_question = asked_questions[-1] if asked_questions else ""

    # Call AI to narrow
    narrow_result = await _ai_narrow_candidates(
        candidates=candidates,
        user_answer=answer,
        original_query=query,
        question_text=last_question,
        asked_questions=asked_questions,
    )

    if narrow_result and narrow_result.get("candidates"):
        # Replace candidates with narrowed list
        new_candidates = []
        for c in narrow_result["candidates"]:
            if isinstance(c, dict) and c.get("title"):
                new_candidates.append({
                    "title": c["title"],
                    "year": c.get("year"),
                    "media_type": c.get("media_type", "movie"),
                    "confidence": c.get("confidence", 0.5),
                    "relevance_reason": c.get("relevance_reason", ""),
                })
        if new_candidates:
            candidates = new_candidates
    else:
        logger.warning("AI narrowing failed, using existing candidates")

    # Update session
    session["candidates"] = candidates
    session["narrowing_round"] = narrowing_round

    candidate_count = len(candidates)
    logger.info(
        "After narrowing round %d: %d candidates remain",
        narrowing_round, candidate_count,
    )

    # Verification: flag if candidate count exceeds 100
    if candidate_count > 100:
        logger.warning(
            "VERIFICATION WARNING: Candidate count %d exceeds 100 after narrowing round %d",
            candidate_count, narrowing_round,
        )

    # Check if more narrowing needed
    if (
        narrowing_round < MAX_NARROWING_ROUNDS
        and candidate_count > TARGET_CANDIDATES
        and narrow_result
        and narrow_result.get("narrowing_question")
    ):
        question = ClarifyingQuestion(
            question=narrow_result["narrowing_question"],
            options=narrow_result.get("narrowing_options", []),
            field=narrow_result.get("narrowing_field", "general"),
        )
        session["asked_questions"].append(question.question)
        return DiscoverResponse(
            session_id=session_id,
            status="asking",
            question=question,
        )

    # Resolve and return final results
    resolved = await _resolve_via_tmdb(
        db, candidates, watched_ids, disliked_ids,
        include_watched, language_prefs, media_type,
    )
    final = await _assemble_final(
        db, resolved, query, genres, media_type, user_id,
        watched_ids, disliked_ids, language_prefs,
    )
    await _enrich_collections(final)

    # Store all resolved results (excluding special picks) for "load more"
    final_ids = {r.tmdb_id for r in final}
    remaining = [r for r in resolved if r.tmdb_id not in final_ids]
    session["all_remaining"] = [r.model_dump() for r in remaining]
    session["more_offset"] = 0

    has_more = len(remaining) > 0
    return DiscoverResponse(session_id=session_id, status="results", results=final, has_more=has_more)
