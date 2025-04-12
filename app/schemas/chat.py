from enum import Enum
from pydantic import BaseModel

class ChatType(str, Enum):
    PERSONAL = "personal"
    GROUP = "group"

class ChatBase(BaseModel):
    name: str
    type: ChatType

class ChatCreate(ChatBase):
    pass

class ChatResponse(ChatBase):
    id: int

    class Config:
        from_attributes = True