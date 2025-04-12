from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Chat, ChatType, group_participants
from typing import Optional, List

class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, chat: Chat) -> Chat:
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    async def get_by_id(self, chat_id: int) -> Optional[Chat]:
        result = await self.session.execute(select(Chat).filter(Chat.id == chat_id))
        return result.scalars().first()

    async def add_participants(self, chat_id: int, user_ids: List[int]):
        chat = await self.get_by_id(chat_id)
        if not chat:
            raise ValueError("Chat not found")
        for user_id in user_ids:
            await self.session.execute(
                "INSERT INTO group_participants (group_id, user_id) VALUES (:group_id, :user_id)",
                {"group_id": chat_id, "user_id": user_id}
            )
        await self.session.commit()

    async def get_personal_chat(self, user1_id: int, user2_id: int) -> Optional[Chat]:

        result = await self.session.execute(
            select(Chat)
            .filter(Chat.type == ChatType.PERSONAL)
            .join(group_participants, Chat.id == group_participants.c.group_id)
            .filter(group_participants.c.user_id.in_([user1_id, user2_id]))
            .group_by(Chat.id)
            .having(func.count(group_participants.c.user_id) == 2)
        )
        return result.scalars().first()

    async def is_participant(self, chat_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(group_participants).filter(
                group_participants.c.group_id == chat_id,
                group_participants.c.user_id == user_id
            )
        )
        return bool(result.first())