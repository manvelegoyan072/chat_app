from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.message_repository import MessageRepository
from app.repositories.chat_repository import ChatRepository
from app.schemas.message import MessageCreate, MessageResponse
from app.models.models import Message
from fastapi import HTTPException
from datetime import datetime
from typing import List


class MessageService:
    def __init__(self, session: AsyncSession):
        self.message_repo = MessageRepository(session)
        self.chat_repo = ChatRepository(session)

    async def send_message(self, message_data: MessageCreate, sender_id: int, message_uuid: str) -> MessageResponse:

        if not await self.chat_repo.get_by_id(message_data.chat_id):
            raise HTTPException(status_code=404, detail="Chat not found")


        if await self.message_repo.get_by_uuid(message_uuid):
            raise HTTPException(status_code=400, detail="Message already exists")

        message = Message(
            chat_id=message_data.chat_id,
            sender_id=sender_id,
            text=message_data.text,
            timestamp=datetime.utcnow(),
            is_read=False,
            uuid=message_uuid
        )
        created_message = await self.message_repo.create(message)
        return MessageResponse.model_validate(created_message)

    async def get_message_history(self, chat_id: int, limit: int = 10, offset: int = 0) -> List[MessageResponse]:
        if not await self.chat_repo.get_by_id(chat_id):
            raise HTTPException(status_code=404, detail="Chat not found")
        messages = await self.message_repo.get_by_chat_id(chat_id, limit, offset)
        return [MessageResponse.model_validate(msg) for msg in messages]

    async def mark_message_as_read(self, message_id: int, user_id: int) -> None:
        message = await self.message_repo.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")


        chat = await self.chat_repo.get_by_id(message.chat_id)
        if not await self.chat_repo.is_participant(chat.id, user_id):
            raise HTTPException(status_code=403, detail="User not in chat")

        if not message.is_read:
            message.is_read = True
            await self.message_repo.update(message)