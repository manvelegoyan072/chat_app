from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Group, group_participants
from typing import Optional

class GroupRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, group: Group) -> Group:
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def get_by_id(self, group_id: int) -> Optional[Group]:
        result = await self.session.execute(select(Group).filter(Group.id == group_id))
        return result.scalars().first()

    async def add_participant(self, group_id: int, user_id: int):
        await self.session.execute(
            "INSERT INTO group_participants (group_id, user_id) VALUES (:group_id, :user_id)",
            {"group_id": group_id, "user_id": user_id}
        )
        await self.session.commit()

    async def remove_participant(self, group_id: int, user_id: int):
        await self.session.execute(
            "DELETE FROM group_participants WHERE group_id = :group_id AND user_id = :user_id",
            {"group_id": group_id, "user_id": user_id}
        )
        await self.session.commit()

    async def is_participant(self, group_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(group_participants).filter(
                group_participants.c.group_id == group_id,
                group_participants.c.user_id == user_id
            )
        )
        return bool(result.first())