import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


class TMDBClient:
    def __init__(self):
        self.api_key = settings.tmdb_api_key
        # Support both v3 API key (short) and v4 read access token (long/Bearer)
        self._is_bearer = len(self.api_key) > 40
        if self._is_bearer:
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
        else:
            self.headers = {"Accept": "application/json"}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        p = dict(params or {})
        if not self._is_bearer:
            p["api_key"] = self.api_key
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{TMDB_BASE_URL}{path}",
                headers=self.headers,
                params=p,
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def test_connection(self) -> bool:
        try:
            data = await self._get("/configuration")
            return "images" in data
        except Exception:
            logger.exception("TMDB connection test failed")
            return False

    async def search_multi(self, query: str, page: int = 1) -> dict:
        return await self._get("/search/multi", {"query": query, "page": page})

    async def search_movie(self, query: str, page: int = 1, year: int | None = None) -> dict:
        params = {"query": query, "page": page}
        if year:
            params["year"] = year
        return await self._get("/search/movie", params)

    async def search_tv(self, query: str, page: int = 1, year: int | None = None) -> dict:
        params = {"query": query, "page": page}
        if year:
            params["first_air_date_year"] = year
        return await self._get("/search/tv", params)

    async def get_movie(self, tmdb_id: int) -> dict:
        return await self._get(
            f"/movie/{tmdb_id}",
            {"append_to_response": "credits,videos,watch/providers,external_ids,release_dates"},
        )

    async def get_tv(self, tmdb_id: int) -> dict:
        return await self._get(
            f"/tv/{tmdb_id}",
            {"append_to_response": "credits,videos,watch/providers,external_ids,content_ratings"},
        )

    async def discover_movies(self, **filters) -> dict:
        return await self._get("/discover/movie", filters)

    async def discover_tv(self, **filters) -> dict:
        return await self._get("/discover/tv", filters)

    async def get_movie_recommendations(self, tmdb_id: int) -> dict:
        return await self._get(f"/movie/{tmdb_id}/recommendations")

    async def get_tv_recommendations(self, tmdb_id: int) -> dict:
        return await self._get(f"/tv/{tmdb_id}/recommendations")

    async def search_person(self, query: str) -> dict:
        return await self._get("/search/person", {"query": query})

    async def get_genre_list(self, media_type: str = "movie") -> dict:
        return await self._get(f"/genre/{media_type}/list")


def parse_movie_to_title_data(movie: dict) -> dict:
    """Convert TMDB movie response to data suitable for Title model."""
    # Extract US content rating
    content_rating = None
    for country in movie.get("release_dates", {}).get("results", []):
        if country.get("iso_3166_1") == "US":
            for release in country.get("release_dates", []):
                if release.get("certification"):
                    content_rating = release["certification"]
                    break

    return {
        "tmdb_id": movie["id"],
        "media_type": "movie",
        "title": movie.get("title", ""),
        "original_title": movie.get("original_title"),
        "overview": movie.get("overview"),
        "tagline": movie.get("tagline"),
        "poster_path": movie.get("poster_path"),
        "backdrop_path": movie.get("backdrop_path"),
        "release_date": movie.get("release_date") or None,
        "runtime": movie.get("runtime"),
        "status": movie.get("status"),
        "vote_average": movie.get("vote_average"),
        "vote_count": movie.get("vote_count"),
        "popularity": movie.get("popularity"),
        "original_language": movie.get("original_language"),
        "content_rating": content_rating,
    }


def parse_tv_to_title_data(show: dict) -> dict:
    """Convert TMDB TV response to data suitable for Title model."""
    content_rating = None
    for result in show.get("content_ratings", {}).get("results", []):
        if result.get("iso_3166_1") == "US":
            content_rating = result.get("rating")
            break

    return {
        "tmdb_id": show["id"],
        "media_type": "tv",
        "title": show.get("name", ""),
        "original_title": show.get("original_name"),
        "overview": show.get("overview"),
        "tagline": show.get("tagline"),
        "poster_path": show.get("poster_path"),
        "backdrop_path": show.get("backdrop_path"),
        "release_date": show.get("first_air_date") or None,
        "runtime": (show.get("episode_run_time") or [None])[0],
        "status": show.get("status"),
        "vote_average": show.get("vote_average"),
        "vote_count": show.get("vote_count"),
        "popularity": show.get("popularity"),
        "original_language": show.get("original_language"),
        "content_rating": content_rating,
        "number_of_seasons": show.get("number_of_seasons"),
        "number_of_episodes": show.get("number_of_episodes"),
    }


def parse_genres(data: dict) -> list[dict]:
    return [{"genre_id": g["id"], "genre_name": g["name"]} for g in data.get("genres", [])]


def parse_credits(data: dict, limit_cast: int = 10) -> list[dict]:
    people = []
    for i, member in enumerate(data.get("credits", {}).get("cast", [])[:limit_cast]):
        people.append({
            "tmdb_person_id": member["id"],
            "name": member["name"],
            "role": "cast",
            "character": member.get("character"),
            "order": member.get("order", i),
            "profile_path": member.get("profile_path"),
        })
    for member in data.get("credits", {}).get("crew", []):
        if member.get("job") in ("Director", "Creator"):
            people.append({
                "tmdb_person_id": member["id"],
                "name": member["name"],
                "role": "director",
                "character": None,
                "order": None,
                "profile_path": member.get("profile_path"),
            })
    return people


def parse_videos(data: dict) -> list[dict]:
    videos = []
    for v in data.get("videos", {}).get("results", []):
        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser", "Clip"):
            videos.append({
                "key": v["key"],
                "site": v["site"],
                "video_type": v["type"],
                "name": v.get("name"),
                "official": v.get("official", False),
            })
    return videos


def parse_watch_providers(data: dict, country: str = "US") -> list[dict]:
    providers = []
    country_data = data.get("watch/providers", {}).get("results", {}).get(country, {})
    for ptype in ("flatrate", "rent", "buy"):
        for p in country_data.get(ptype, []):
            providers.append({
                "provider_id": p["provider_id"],
                "provider_name": p["provider_name"],
                "logo_path": p.get("logo_path"),
                "provider_type": ptype,
                "country": country,
            })
    return providers


def parse_external_ids(data: dict) -> list[dict]:
    ids = []
    ext = data.get("external_ids", {})
    if ext.get("imdb_id"):
        ids.append({"source": "imdb", "external_id": ext["imdb_id"]})
    if ext.get("tvdb_id"):
        ids.append({"source": "tvdb", "external_id": str(ext["tvdb_id"])})
    return ids


tmdb_client = TMDBClient()
