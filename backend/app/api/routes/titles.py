from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.title import TitleOut, TitleSearchResponse
from app.services.title_service import fetch_and_store_title, search_titles

router = APIRouter()


@router.get("/titles/search", response_model=TitleSearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    media_type: str | None = Query(None, pattern="^(movie|tv)$"),
    page: int = Query(1, ge=1),
):
    return await search_titles(q, media_type=media_type, page=page)


@router.get("/titles/{tmdb_id}", response_model=TitleOut)
async def get_title(
    tmdb_id: int,
    media_type: str = Query("movie", pattern="^(movie|tv)$"),
    db: AsyncSession = Depends(get_db),
):
    title = await fetch_and_store_title(db, tmdb_id, media_type)
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    return title
