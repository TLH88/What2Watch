import logging
import re
import uuid

from app.schemas.recall import (
    ExtractedClues,
    NarrowingQuestion,
    RecallCandidate,
    RecallResponse,
)
from app.services.integrations.tmdb import tmdb_client

logger = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}

DECADE_PATTERNS = {
    "50s": (1950, 1959), "60s": (1960, 1969), "70s": (1970, 1979),
    "80s": (1980, 1989), "90s": (1990, 1999), "2000s": (2000, 2009),
    "2010s": (2010, 2019), "2020s": (2020, 2029),
}

TONE_KEYWORDS = {
    "funny": "comedy", "scary": "horror", "dark": "dark", "sad": "drama",
    "romantic": "romance", "creepy": "horror", "intense": "thriller",
    "lighthearted": "comedy", "goofy": "comedy", "violent": "action",
    "mysterious": "mystery", "suspenseful": "thriller",
}

# TMDB genre IDs for discover API filtering
GENRE_IDS = {
    "comedy": 35, "horror": 27, "drama": 18, "romance": 10749,
    "thriller": 53, "action": 28, "mystery": 9648, "dark": 53,
    "sci-fi": 878, "fantasy": 14, "animation": 16, "adventure": 12,
    "crime": 80, "war": 10752, "western": 37, "documentary": 99,
}
TV_GENRE_IDS = {
    "comedy": 35, "horror": 27, "drama": 18, "romance": 10749,
    "thriller": 53, "action": 10759, "mystery": 9648, "dark": 53,
    "sci-fi": 10765, "fantasy": 10765, "animation": 16, "adventure": 10759,
    "crime": 80, "war": 10768, "western": 37, "documentary": 99,
}


def extract_clues(description: str) -> ExtractedClues:
    """Extract structured clues from a free-text description."""
    d = description.lower().strip()
    clues = ExtractedClues()

    # Media type
    if any(w in d for w in ["tv show", "series", "show", "episode", "season"]):
        clues.media_type = "tv"
    elif any(w in d for w in ["movie", "film"]):
        clues.media_type = "movie"

    # Animated
    if any(w in d for w in ["animated", "animation", "cartoon", "anime"]):
        clues.is_animated = True
    elif any(w in d for w in ["live action", "live-action", "real actors"]):
        clues.is_animated = False

    # Era/decade
    for label, (start, end) in DECADE_PATTERNS.items():
        if label in d:
            clues.era = label
            break
    if not clues.era:
        year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', d)
        if year_match:
            year = int(year_match.group())
            decade = (year // 10) * 10
            clues.era = f"{decade}s" if decade >= 2000 else f"{str(decade)[2:]}s"

    # Tone
    for keyword, tone in TONE_KEYWORDS.items():
        if keyword in d:
            clues.tone = tone
            break

    # Country/setting
    countries = ["american", "british", "french", "japanese", "korean", "italian",
                 "spanish", "german", "indian", "chinese", "australian", "mexican"]
    for c in countries:
        if c in d:
            clues.country = c
            break

    settings = ["space", "desert", "ocean", "underwater", "jungle", "city",
                "small town", "island", "prison", "school", "hospital", "war"]
    for s in settings:
        if s in d:
            clues.setting = s
            break

    # Extract potential actor names
    # Look for "with/starring [Name Name]" patterns
    actor_patterns = re.findall(
        r'(?:with|starring|actor|actress|played by|directed by|features?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        description,
    )
    # Also look for any sequence of 2+ capitalized words (likely proper names)
    name_patterns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', description)
    # Filter out common non-name phrases
    skip = {"The Matrix", "The Movie", "The Film", "The Show", "Not Sure", "TV Show"}
    all_names = []
    for n in actor_patterns + name_patterns:
        if n not in skip and n not in all_names:
            all_names.append(n)
    clues.actors = all_names[:3]

    # Keywords — significant words for search
    # Collect actor name words to exclude from keywords
    actor_words = set()
    for actor in clues.actors:
        for w in actor.lower().split():
            actor_words.add(w)

    stop_words = {"the", "a", "an", "it", "was", "is", "about", "this", "that", "there",
                  "where", "when", "who", "what", "had", "has", "have", "were", "are",
                  "been", "being", "they", "them", "their", "some", "with", "from",
                  "but", "and", "for", "not", "you", "all", "can", "her", "his",
                  "one", "our", "out", "its", "also", "just", "than", "then", "she",
                  "him", "how", "man", "old", "new", "now", "way", "may", "say",
                  "each", "which", "movie", "film", "show", "series", "remember",
                  "think", "saw", "watched", "like", "scene", "part", "something",
                  "guy", "girl", "woman", "really", "very", "much", "know", "thing",
                  "starring", "actor", "actress", "played", "directed", "features"}
    words = re.findall(r'\b[a-z]{3,}\b', d)
    clues.keywords = [w for w in words if w not in stop_words and w not in actor_words][:8]

    # Plot details — extract sentences that seem descriptive
    sentences = re.split(r'[.!?]+', description)
    for s in sentences:
        s = s.strip()
        if len(s) > 15 and any(w in s.lower() for w in ["about", "where", "who", "plot", "story", "end", "dies", "kills", "finds", "discovers", "escapes", "falls"]):
            clues.plot_details.append(s)

    return clues


async def search_by_clues(clues: ExtractedClues) -> list[RecallCandidate]:
    """Search TMDB using extracted clues, cast a wide net, then score by overview matching."""
    candidates: list[RecallCandidate] = []
    seen_ids: set[int] = set()

    def _add_candidate(item: dict, mt: str, reason: str, base_confidence: float = 0.0):
        tid = item["id"]
        if tid in seen_ids:
            # If already seen but new reason has higher base confidence, update it
            for existing in candidates:
                if existing.tmdb_id == tid and base_confidence > existing.confidence:
                    existing.confidence = base_confidence
                    existing.match_reasons = [reason]
            return
        seen_ids.add(tid)
        if clues.media_type and mt != clues.media_type:
            return
        candidates.append(RecallCandidate(
            tmdb_id=tid,
            media_type=mt,
            title=item.get("title") or item.get("name", ""),
            year=_extract_year(item),
            overview=item.get("overview"),
            poster_path=item.get("poster_path"),
            vote_average=item.get("vote_average"),
            match_reasons=[reason],
            confidence=base_confidence,
        ))

    # 1. Search by actor name — high-value signal
    for actor in clues.actors:
        try:
            person_results = await tmdb_client.search_person(actor)
            for person in person_results.get("results", [])[:3]:
                known_for = person.get("known_for", [])
                for item in known_for:
                    mt = item.get("media_type", "movie")
                    _add_candidate(item, mt, f"Features {actor}", 40.0)  # known_for = most famous roles
                # Also get their full filmography via person credits
                person_id = person["id"]
                try:
                    credits = await tmdb_client._get(f"/person/{person_id}/combined_credits")
                    cast_list = credits.get("cast", [])
                    # Filter to relevant media type and exclude talk shows/cameos
                    filtered = []
                    for item in cast_list:
                        mt = item.get("media_type", "movie")
                        # Skip if user specified a media type and this doesn't match
                        if clues.media_type and mt != clues.media_type:
                            continue
                        # Skip talk shows and variety (genre_ids containing 10767)
                        if 10767 in item.get("genre_ids", []):
                            continue
                        filtered.append(item)
                    # Sort by vote_count (better signal than popularity for filmography)
                    filtered.sort(key=lambda x: x.get("vote_count", 0), reverse=True)
                    for rank, item in enumerate(filtered[:20]):
                        mt = item.get("media_type", "movie")
                        # Higher-ranked (more voted) titles get a larger boost
                        rank_boost = max(0, 10 - rank)  # Top result +10, second +9, etc.
                        _add_candidate(item, mt, f"Features {actor}", 30.0 + rank_boost)
                except Exception:
                    pass
        except Exception:
            logger.warning(f"Actor search failed for: {actor}")

    # 2. Build diverse search queries — individual keywords as title searches
    search_queries = []
    if clues.keywords:
        # Each keyword individually (catches titles containing that word)
        for kw in clues.keywords[:6]:
            if len(kw) > 3:
                search_queries.append(kw)
        # Pairs of keywords
        for i in range(0, min(len(clues.keywords), 6), 2):
            chunk = clues.keywords[i:i+2]
            if len(chunk) == 2:
                search_queries.append(" ".join(chunk))

    if clues.plot_details:
        detail = clues.plot_details[0]
        content_words = [w for w in detail.split() if len(w) > 3 and w.lower() not in
                        {"this", "that", "from", "where", "about", "there", "with",
                         "movie", "film", "show", "remember", "think", "were", "have"}]
        if content_words:
            search_queries.append(" ".join(content_words[:4]))

    # Deduplicate
    seen_q: set[str] = set()
    unique_queries = []
    for q in search_queries:
        ql = q.lower()
        if ql not in seen_q:
            seen_q.add(ql)
            unique_queries.append(q)
    search_queries = unique_queries

    # 3. Keyword-based search — fetch more results per query
    for query in search_queries[:6]:
        try:
            if clues.media_type == "movie":
                data = await tmdb_client.search_movie(query)
            elif clues.media_type == "tv":
                data = await tmdb_client.search_tv(query)
            else:
                data = await tmdb_client.search_multi(query)

            for item in data.get("results", [])[:15]:
                mt = item.get("media_type", clues.media_type or "movie")
                if mt not in ("movie", "tv"):
                    continue
                _add_candidate(item, mt, f"Search: {query}")
        except Exception:
            logger.warning(f"Keyword search failed for: {query}")

    # 4. Discover API — cast a wide net using genre/era filters
    discover_filters: dict = {"sort_by": "popularity.desc"}
    if clues.tone and clues.tone in GENRE_IDS:
        genre_map = TV_GENRE_IDS if clues.media_type == "tv" else GENRE_IDS
        gid = genre_map.get(clues.tone)
        if gid:
            discover_filters["with_genres"] = str(gid)
    if clues.is_animated is True:
        anim_id = 16
        existing = discover_filters.get("with_genres", "")
        discover_filters["with_genres"] = f"{existing},{anim_id}" if existing else str(anim_id)
    if clues.era:
        era_range = DECADE_PATTERNS.get(clues.era)
        if era_range:
            if clues.media_type == "tv":
                discover_filters["first_air_date.gte"] = f"{era_range[0]}-01-01"
                discover_filters["first_air_date.lte"] = f"{era_range[1]}-12-31"
            else:
                discover_filters["primary_release_date.gte"] = f"{era_range[0]}-01-01"
                discover_filters["primary_release_date.lte"] = f"{era_range[1]}-12-31"

    try:
        if clues.media_type == "tv":
            data = await tmdb_client.discover_tv(**discover_filters)
        elif clues.media_type == "movie":
            data = await tmdb_client.discover_movies(**discover_filters)
        else:
            # Search both
            data = await tmdb_client.discover_movies(**discover_filters)
            for item in data.get("results", [])[:20]:
                _add_candidate(item, "movie", "Discover match")
            data = await tmdb_client.discover_tv(**discover_filters)

        for item in data.get("results", [])[:20]:
            mt = "tv" if clues.media_type == "tv" else item.get("media_type", clues.media_type or "movie")
            if "name" in item and "title" not in item:
                mt = "tv"
            _add_candidate(item, mt, "Discover match")
    except Exception:
        logger.warning("Discover search failed")

    # 5. Score all candidates — heavily weight overview text matching
    all_description_words = _get_description_words(clues)
    for c in candidates:
        base = c.confidence
        c.confidence = base + _score_candidate(c, clues, all_description_words)

    # Sort by confidence and return top results
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:8]


def _get_description_words(clues: ExtractedClues) -> set[str]:
    """Build a set of all meaningful words from the user's description for overview matching."""
    words: set[str] = set()
    # Keywords
    for kw in clues.keywords:
        words.add(kw.lower())
    # Actor names (split into individual words for overview matching)
    for actor in clues.actors:
        for w in actor.lower().split():
            if len(w) > 2:
                words.add(w)
    # Plot detail words
    skip = {"this", "that", "from", "where", "about", "there", "with", "movie", "film",
            "show", "remember", "think", "were", "have", "they", "them", "their", "been",
            "some", "what", "when", "which", "would", "could", "should", "does", "into"}
    for detail in clues.plot_details:
        for w in detail.lower().split():
            w = re.sub(r'[^a-z]', '', w)
            if len(w) > 3 and w not in skip:
                words.add(w)
    return words


def _extract_year(item: dict) -> str | None:
    d = item.get("release_date") or item.get("first_air_date")
    return d[:4] if d and len(d) >= 4 else None


def _score_candidate(
    candidate: RecallCandidate,
    clues: ExtractedClues,
    description_words: set[str] | None = None,
) -> float:
    score = 0.0
    overview = (candidate.overview or "").lower()
    title = candidate.title.lower()
    combined_text = f"{overview} {title}"

    # PRIMARY: Match all description words against overview text (up to 50 pts)
    # This is the core scoring mechanism — overview contains actor names,
    # character names, plot details, and genre keywords from TMDB
    # We separately check overview and title to avoid title-only false positives
    if description_words:
        overview_matches = sum(1 for w in description_words if w in overview)
        title_matches = sum(1 for w in description_words if w in title and w not in overview)
        # Overview matches are worth much more than title-only matches
        if len(description_words) > 0:
            overview_ratio = overview_matches / len(description_words)
            score += overview_ratio * 50
            # Title-only matches get a small boost (could be coincidental)
            score += title_matches * 3
            # Bonus for high overview match count
            if overview_matches >= 3:
                score += min(overview_matches * 3, 20)

    # Keyword matches in overview specifically (up to 30 pts)
    if clues.keywords:
        overview_kw_matches = sum(1 for kw in clues.keywords if kw in overview)
        title_kw_matches = sum(1 for kw in clues.keywords if kw in title)
        kw_score = (overview_kw_matches / len(clues.keywords)) * 30
        # Small bonus for title keyword match
        kw_score += min(title_kw_matches * 2, 6)
        score += kw_score

    # Actor name in overview (15 pts each — names appear in TMDB overview/credits)
    if clues.actors:
        for actor in clues.actors:
            name_parts = actor.lower().split()
            # Check if surname appears in overview (most distinctive part)
            if len(name_parts) >= 2 and name_parts[-1] in overview:
                score += 15
            elif actor.lower() in overview:
                score += 15

    # Era match (20 pts exact, 10 pts close)
    if clues.era and candidate.year:
        era_range = DECADE_PATTERNS.get(clues.era)
        if era_range:
            try:
                y = int(candidate.year)
                if era_range[0] <= y <= era_range[1]:
                    score += 20
                elif abs(y - era_range[0]) <= 5:
                    score += 10
            except ValueError:
                pass

    # Tone match
    if clues.tone and clues.tone in overview:
        score += 10

    # Setting match
    if clues.setting and clues.setting in overview:
        score += 15

    # Country match
    if clues.country and clues.country in overview:
        score += 10

    # Animated match
    if clues.is_animated is True and "animat" in overview:
        score += 10
    elif clues.is_animated is False and "animat" not in overview:
        score += 5

    # Popularity tiebreaker (small)
    if candidate.vote_average:
        score += candidate.vote_average * 0.3

    return round(score, 1)


def get_narrowing_question(clues: ExtractedClues, questions_asked: int) -> NarrowingQuestion | None:
    """Return the most useful narrowing question based on missing clues."""
    if not clues.media_type and questions_asked < 1:
        return NarrowingQuestion(
            question="Was it a movie or a TV series?",
            options=["Movie", "TV Series", "Not sure"],
            field="media_type",
        )
    if clues.is_animated is None and questions_asked < 2:
        return NarrowingQuestion(
            question="Was it animated or live action?",
            options=["Animated", "Live Action", "Not sure"],
            field="is_animated",
        )
    if not clues.era and questions_asked < 3:
        return NarrowingQuestion(
            question="Roughly what decade was it from?",
            options=["80s or earlier", "90s", "2000s", "2010s", "2020s", "Not sure"],
            field="era",
        )
    return None


def apply_narrowing_answer(clues: ExtractedClues, field: str, answer: str) -> ExtractedClues:
    a = answer.lower().strip()
    if field == "media_type":
        if "movie" in a:
            clues.media_type = "movie"
        elif "tv" in a or "series" in a:
            clues.media_type = "tv"
    elif field == "is_animated":
        if "animated" in a:
            clues.is_animated = True
        elif "live" in a:
            clues.is_animated = False
    elif field == "era":
        if "not sure" not in a:
            for label in DECADE_PATTERNS:
                if label in a:
                    clues.era = label
                    break
            if not clues.era and "earlier" in a:
                clues.era = "80s"
    return clues


async def start_recall(description: str) -> RecallResponse:
    session_id = str(uuid.uuid4())
    clues = extract_clues(description)

    # Always try searching first when we have any clues
    candidates = await search_by_clues(clues)
    _sessions[session_id] = {"clues": clues, "candidates": candidates, "questions_asked": 0}

    if candidates:
        return RecallResponse(
            session_id=session_id, status="candidates",
            clues=clues, candidates=candidates[:5],
        )

    # No results — ask narrowing questions to refine
    question = get_narrowing_question(clues, 0)
    if question:
        return RecallResponse(
            session_id=session_id, status="asking",
            clues=clues, question=question,
        )

    return RecallResponse(
        session_id=session_id, status="candidates",
        clues=clues, candidates=[],
    )


async def respond_recall(session_id: str, answer: str) -> RecallResponse:
    session = _sessions.get(session_id)
    if not session:
        return RecallResponse(session_id=session_id, status="candidates")

    clues: ExtractedClues = session["clues"]
    questions_asked: int = session.get("questions_asked", 0)

    # Apply the answer
    question = get_narrowing_question(clues, questions_asked)
    if question:
        clues = apply_narrowing_answer(clues, question.field, answer)
        session["clues"] = clues
        session["questions_asked"] = questions_asked + 1

    # Check if we should ask another question or search
    next_q = get_narrowing_question(clues, questions_asked + 1)
    if next_q and questions_asked < 2:
        return RecallResponse(
            session_id=session_id, status="asking",
            clues=clues, question=next_q,
        )

    # Search with refined clues
    candidates = await search_by_clues(clues)
    session["candidates"] = candidates
    return RecallResponse(
        session_id=session_id, status="candidates",
        clues=clues, candidates=candidates[:5],
    )
