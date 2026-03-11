from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.recall import (
    RecallConfirmRequest,
    RecallRespondRequest,
    RecallResponse,
    RecallStartRequest,
)
from app.services.recall_service import respond_recall, start_recall

router = APIRouter()


@router.post("/recall/start", response_model=RecallResponse)
async def recall_start(data: RecallStartRequest):
    return await start_recall(data.description)


@router.post("/recall/respond", response_model=RecallResponse)
async def recall_respond(data: RecallRespondRequest):
    return await respond_recall(data.session_id, data.answer)


@router.post("/recall/confirm")
async def recall_confirm(data: RecallConfirmRequest):
    return {"status": "confirmed", "tmdb_id": data.tmdb_id}
