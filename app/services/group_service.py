from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.group_repository import GroupRepository
from app.repositories.user_repository import UserRepository
from app.schemas.group import GroupResponse
from fastapi import HTTPException

class GroupService:
    def __init__(self, session: AsyncSession):
        self.group_repo = GroupRepository(session)
        self.user_repo = UserRepository(session)

    async def add_participant(self, group_id: int, user_id: int):
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if not await self.user_repo.get_by_id(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        if await self.group_repo.is_participant(group_id, user_id):
            raise HTTPException(status_code=400, detail="User already in group")
        await self.group_repo.add_participant(group_id, user_id)

    async def remove_participant(self, group_id: int, user_id: int):
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if not await self.group_repo.is_participant(group_id, user_id):
            raise HTTPException(status_code=400, detail="User not in group")
        await self.group_repo.remove_participant(group_id, user_id)

    async def get_group_by_id(self, group_id: int) -> GroupResponse:
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        return GroupResponse.model_validate(group)