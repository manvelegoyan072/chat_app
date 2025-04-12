from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.message_service import MessageService
from app.schemas.message import MessageResponse
from app.config import get_db
from app.main import get_current_user
from typing import List

router = APIRouter(prefix="/history", tags=["Messages"])

@router.get("/{chat_id}", response_model=List[MessageResponse])
async def get_message_history(
    chat_id: int,
    limit: int = 10,
    offset: int = 0,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    message_service = MessageService(db)
    return await message_service.get_message_history(chat_id, limit, offset)