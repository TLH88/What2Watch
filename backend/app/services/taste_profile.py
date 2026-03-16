"""Taste profile generation: deterministic stats + AI polish."""
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.title import Title, TitleGenre, TitlePerson
from app.models.user import UserFeedback, UserPreferences
from app.services.ai.provider import get_ai_provider

logger = logging.getLogger(__name__)

TASTE_PROFILE_SYSTEM = """\
You are a concise movie/TV taste analyst. Given viewing statistics as JSON, \
write a 2-3 sentence natural language taste profile. Be specific about genres, \
eras, and patterns. Don't use the viewer's name. Write in third person \
(e.g. "Gravitates toward..." or "Prefers..."). Keep it under 80 words.

Respond with JSON: {"profile": "your 2-3 sentence profile here"}"""


async def _gather_stats(db: AsyncSession, user_id: int) -> dict:
    """Query feedback + title metadata to build raw taste stats."""
    # Load all feedback with title details
    fb_result = await db.execute(
        select(UserFeedback, Title)
        .join(Title, UserFeedback.title_id == Title.id)
        .where(UserFeedback.user_id == user_id)
        .options(
            selectinload(Title.genres),
            selectinload(Title.people),
        )
    )
    rows = fb_result.all()

    if not rows:
        return {}

    # Separate liked/disliked titles
    liked_titles: list[Title] = []
    disliked_titles: list[Title] = []
    for fb, title in rows:
        if fb.feedback_type == "thumbs_up":
            liked_titles.append(title)
        elif fb.feedback_type == "thumbs_down":
            disliked_titles.append(title)

    # Genre affinity
    genre_likes: Counter = Counter()
    genre_dislikes: Counter = Counter()
    for t in liked_titles:
        for g in t.genres:
            genre_likes[g.genre_name] += 1
    for t in disliked_titles:
        for g in t.genres:
            genre_dislikes[g.genre_name] += 1

    # Net genre scores sorted by affinity
    all_genres = set(genre_likes.keys()) | set(genre_dislikes.keys())
    genre_scores = {}
    for g in all_genres:
        genre_scores[g] = {
            "liked": genre_likes.get(g, 0),
            "disliked": genre_dislikes.get(g, 0),
            "net": genre_likes.get(g, 0) - genre_dislikes.get(g, 0),
        }
    top_genres = sorted(genre_scores.items(), key=lambda x: x[1]["net"], reverse=True)

    # Top directors (2+ liked titles)
    director_counts: Counter = Counter()
    for t in liked_titles:
        for p in t.people:
            if p.role == "director":
                director_counts[p.name] += 1
    top_directors = [
        {"name": name, "count": count}
        for name, count in director_counts.most_common(10)
        if count >= 2
    ]

    # Decade distribution (liked only)
    decade_counts: Counter = Counter()
    for t in liked_titles:
        if t.release_date:
            decade = (t.release_date.year // 10) * 10
            decade_counts[f"{decade}s"] += 1
    total_with_date = sum(decade_counts.values()) or 1
    decade_dist = {
        d: round(c / total_with_date * 100)
        for d, c in decade_counts.most_common()
    }

    # Content rating distribution (liked only)
    rating_counts: Counter = Counter()
    for t in liked_titles:
        if t.content_rating:
            rating_counts[t.content_rating] += 1

    # Average runtime and quality (liked only)
    runtimes = [t.runtime for t in liked_titles if t.runtime]
    avg_runtime = round(sum(runtimes) / len(runtimes)) if runtimes else None

    vote_avgs = [t.vote_average for t in liked_titles if t.vote_average]
    avg_quality = round(sum(vote_avgs) / len(vote_avgs), 1) if vote_avgs else None

    # Media type split
    movie_count = sum(1 for t in liked_titles if t.media_type == "movie")
    tv_count = sum(1 for t in liked_titles if t.media_type == "tv")

    return {
        "total_liked": len(liked_titles),
        "total_disliked": len(disliked_titles),
        "top_genres": [
            {"genre": g, "liked": s["liked"], "disliked": s["disliked"]}
            for g, s in top_genres[:10]
        ],
        "top_directors": top_directors,
        "decade_distribution": decade_dist,
        "content_ratings": dict(rating_counts.most_common()),
        "avg_runtime_minutes": avg_runtime,
        "avg_quality_score": avg_quality,
        "media_split": {"movies": movie_count, "tv_shows": tv_count},
    }


def _fallback_profile(stats: dict) -> str:
    """Generate a template-based profile when AI is unavailable."""
    if not stats or stats.get("total_liked", 0) == 0:
        return "Not enough data to generate a taste profile yet."

    parts = []

    # Top genres
    top = [g["genre"] for g in stats.get("top_genres", [])[:3] if g.get("liked", 0) > 0]
    if top:
        parts.append(f"Prefers {', '.join(top[:-1])} and {top[-1]}" if len(top) > 1 else f"Prefers {top[0]}")

    # Decades
    decades = stats.get("decade_distribution", {})
    if decades:
        top_decades = list(decades.keys())[:2]
        parts.append(f"mostly from the {' and '.join(top_decades)}")

    # Quality
    avg_q = stats.get("avg_quality_score")
    if avg_q:
        parts.append(f"Leans toward {'higher' if avg_q >= 7.0 else 'moderately'}-rated titles (avg {avg_q})")

    # Media split
    split = stats.get("media_split", {})
    movies = split.get("movies", 0)
    tv = split.get("tv_shows", 0)
    if movies and tv:
        ratio = movies / (movies + tv)
        if ratio > 0.7:
            parts.append("Primarily watches movies")
        elif ratio < 0.3:
            parts.append("Primarily watches TV shows")

    return ". ".join(parts) + "." if parts else "Not enough data to generate a taste profile yet."


async def generate_taste_profile(db: AsyncSession, user_id: int) -> str:
    """Generate a taste profile for a user. Returns the profile text."""
    stats = await _gather_stats(db, user_id)

    if not stats or stats.get("total_liked", 0) == 0:
        return "Not enough data to generate a taste profile yet."

    raw_json = json.dumps(stats, indent=2)

    # Load prefs to check for cached prompt fallback
    prefs_result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = prefs_result.scalar_one_or_none()

    # Try AI polish
    profile_text = None
    provider = get_ai_provider()
    if provider:
        try:
            response = await provider.chat(
                TASTE_PROFILE_SYSTEM,
                f"Here are the viewing statistics:\n{raw_json}",
            )
            if response:
                # Parse JSON wrapper if present
                try:
                    parsed = json.loads(response.strip())
                    if isinstance(parsed, dict) and "profile" in parsed:
                        profile_text = parsed["profile"].strip()
                except (json.JSONDecodeError, ValueError):
                    # If not JSON, use raw text
                    if len(response.strip()) > 10:
                        profile_text = response.strip()
        except Exception:
            logger.exception("AI taste profile generation failed")

    # Fallback: use last AI-generated profile if available, otherwise template
    if not profile_text:
        if prefs and prefs.taste_profile:
            # Reuse last AI-generated profile
            logger.info("AI unavailable, reusing last AI-generated profile for user %d", user_id)
            profile_text = prefs.taste_profile
        else:
            profile_text = _fallback_profile(stats)

    # Store profile
    if prefs:
        prefs.taste_profile = profile_text
        prefs.taste_profile_raw = raw_json
        prefs.taste_profile_updated_at = datetime.utcnow()
    else:
        prefs = UserPreferences(
            user_id=user_id,
            taste_profile=profile_text,
            taste_profile_raw=raw_json,
            taste_profile_updated_at=datetime.utcnow(),
        )
        db.add(prefs)

    await db.commit()
    return profile_text
