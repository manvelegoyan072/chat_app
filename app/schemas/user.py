from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.USER  # Дефолтная роль

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole

    class Config:
        from_attributes = True