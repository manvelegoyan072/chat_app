from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.message_service import MessageService
from app.schemas.message import MessageResponse
from app.config import get_db
from app.main import get_current_user, CurrentUser
from typing import List
import logging

router = APIRouter(prefix="/history", tags=["Messages"])
logger = logging.getLogger(__name__)


@router.get("/{chat_id}", response_model=List[MessageResponse])
async def get_chat_history(
        chat_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"Fetching history for chat: {chat_id}")
    from app.services.chat_service import ChatService
    chat_service = ChatService(db)
    if not await chat_service.chat_repo.is_participant(chat_id, current_user.id):
        logger.warning(f"User {current_user.id} not authorized for chat: {chat_id}")
        raise HTTPException(status_code=403, detail="Not authorized to view this chat")

    message_service = MessageService(db)
    messages = await message_service.get_chat_history(chat_id)
    logger.debug(f"Retrieved {len(messages)} messages for chat: {chat_id}")
    return [MessageResponse.model_validate(msg) for msg in messages]