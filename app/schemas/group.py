from pydantic import BaseModel
from typing import List

class GroupBase(BaseModel):
    name: str

class GroupCreate(GroupBase):
    participant_ids: List[int]  # Список ID участников группы

class GroupResponse(GroupBase):
    id: int
    creator_id: int
    participants: List["UserResponse"]  # Ссылка на схему пользователей

    class Config:
        from_attributes = True