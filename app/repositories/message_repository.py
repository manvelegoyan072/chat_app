from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Message
from typing import Optional, List

class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_by_id(self, message_id: int) -> Optional[Message]:
        result = await self.session.execute(select(Message).filter(Message.id == message_id))
        return result.scalars().first()

    async def get_by_uuid(self, uuid: str) -> Optional[Message]:
        result = await self.session.execute(select(Message).filter(Message.uuid == uuid))
        return result.scalars().first()

    async def get_by_chat_id(self, chat_id: int, limit: int, offset: int) -> List[Message]:
        result = await self.session.execute(
            select(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.timestamp.asc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update(self, message: Message):
        await self.session.merge(message)
        await self.session.commit()