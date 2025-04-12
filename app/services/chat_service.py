from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.chat_repository import ChatRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.user_repository import UserRepository
from app.schemas.chat import ChatCreate, ChatResponse
from app.models.models import Chat, ChatType
from fastapi import HTTPException


class ChatService:
    def __init__(self, session: AsyncSession):
        self.chat_repo = ChatRepository(session)
        self.group_repo = GroupRepository(session)
        self.user_repo = UserRepository(session)

    async def create_personal_chat(self, user1_id: int, user2_id: int) -> ChatResponse:

        if not await self.user_repo.get_by_id(user1_id) or not await self.user_repo.get_by_id(user2_id):
            raise HTTPException(status_code=404, detail="User not found")


        existing_chat = await self.chat_repo.get_personal_chat(user1_id, user2_id)
        if existing_chat:
            raise HTTPException(status_code=400, detail="Personal chat already exists")

        chat = Chat(
            name=f"Chat {user1_id}-{user2_id}",
            type=ChatType.PERSONAL
        )
        created_chat = await self.chat_repo.create(chat)


        await self.chat_repo.add_participants(created_chat.id, [user1_id, user2_id])
        return ChatResponse.model_validate(created_chat)

    async def create_group_chat(self, chat_data: ChatCreate, creator_id: int) -> ChatResponse:

        if not await self.user_repo.get_by_id(creator_id):
            raise HTTPException(status_code=404, detail="Creator not found")

        chat = Chat(
            name=chat_data.name,
            type=ChatType.GROUP
        )
        created_chat = await self.chat_repo.create(chat)


        await self.group_repo.create_group(created_chat.id, creator_id, chat_data.name)
        return ChatResponse.model_validate(created_chat)

    async def get_chat_by_id(self, chat_id: int) -> ChatResponse:
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        return ChatResponse.model_validate(chat)