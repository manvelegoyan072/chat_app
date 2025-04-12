from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.group_repository import GroupRepository
from app.models.models import Group
from app.schemas.user import UserRole
from fastapi import HTTPException


class GroupService:
    def __init__(self, session: AsyncSession):
        self.group_repo = GroupRepository(session)

    async def create_group(self, chat_id: int, creator_id: int, name: str) -> Group:
        group = Group(name=name, creator_id=creator_id, chat_id=chat_id)
        return await self.group_repo.create(group)

    async def add_participant(self, group_id: int, user_id: int, current_user_id: int):
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Проверка: только создатель (админ группы) может добавлять участников
        if group.creator_id != current_user_id:
            from app.services.user_service import UserService
            user_service = UserService(self.group_repo.session)
            is_admin = await user_service.check_user_role(current_user_id, UserRole.ADMIN)
            if not is_admin:
                raise HTTPException(status_code=403, detail="Only group creator or admin can add participants")

        await self.group_repo.add_participant(group_id, user_id)

    async def remove_participant(self, group_id: int, user_id: int, current_user_id: int):
        group = await self.group_repo.get_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        # Аналогичная проверка для удаления
        if group.creator_id != current_user_id:
            from app.services.user_service import UserService
            user_service = UserService(self.group_repo.session)
            is_admin = await user_service.check_user_role(current_user_id, UserRole.ADMIN)
            if not is_admin:
                raise HTTPException(status_code=403, detail="Only group creator or admin can remove participants")

        await self.group_repo.remove_participant(group_id, user_id)