from pydantic import BaseModel
from typing import List

class GroupBase(BaseModel):
    name: str

class GroupCreate(GroupBase):
    participant_ids: List[int]

class GroupResponse(GroupBase):
    id: int
    creator_id: int
    participants: List["UserResponse"]

    class Config:
        from_attributes = True