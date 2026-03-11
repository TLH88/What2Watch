from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.integrations.tmdb import tmdb_client

router = APIRouter()


@router.post("/integrations/tmdb/test")
async def test_tmdb():
    ok = await tmdb_client.test_connection()
    if not ok:
        raise HTTPException(status_code=503, detail="TMDB connection failed")
    return {"status": "connected"}


@router.post("/integrations/jellyfin/test")
async def test_jellyfin():
    from app.services.integrations.jellyfin import jellyfin_client

    ok = await jellyfin_client.test_connection()
    if not ok:
        raise HTTPException(status_code=503, detail="Jellyfin connection failed")
    return {"status": "connected"}


@router.post("/integrations/jellyfin/sync")
async def sync_jellyfin(db: AsyncSession = Depends(get_db)):
    from app.services.integrations.jellyfin import sync_jellyfin_availability

    count = await sync_jellyfin_availability(db)
    return {"status": "ok", "matched": count}


@router.post("/integrations/trakt/sync")
async def sync_trakt(user_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.integrations.trakt import sync_trakt_history

    count = await sync_trakt_history(db, user_id)
    return {"status": "ok", "imported": count}
