from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserRole
from app.models.models import User, RefreshToken
from fastapi import HTTPException
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import uuid
import os

class UserService:
    def __init__(self, session: AsyncSession):
        self.user_repo = UserRepository(session)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.session = session

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        if await self.user_repo.get_by_email(user_data.email):
            raise HTTPException(status_code=400, detail="Email already exists")
        if len(user_data.name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

        user = User(
            name=user_data.name,
            email=user_data.email,
            password=self.pwd_context.hash(user_data.password),
            role=user_data.role
        )
        created_user = await self.user_repo.create(user)
        return UserResponse.model_validate(created_user)

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(user)

    async def get_user_by_email(self, email: str) -> UserResponse:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse.model_validate(user)

    async def authenticate_user(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email)
        if not user or not self.pwd_context.verify(password, user.password):
            return None
        return user

    async def create_refresh_token(self, user_id: int) -> str:
        refresh_token_expires = timedelta(days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")))
        expires_at = datetime.utcnow() + refresh_token_expires
        token = str(uuid.uuid4())
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        self.session.add(refresh_token)
        await self.session.commit()
        return token

    async def get_refresh_token(self, token: str) -> RefreshToken:
        from sqlalchemy import select
        result = await self.session.execute(
            select(RefreshToken).filter(RefreshToken.token == token)
        )
        refresh_token = result.scalars().first()
        if not refresh_token or refresh_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        return refresh_token

    async def delete_refresh_token(self, token: str):
        refresh_token = await self.get_refresh_token(token)
        await self.session.delete(refresh_token)
        await self.session.commit()

    async def check_user_role(self, user_id: int, required_role: UserRole) -> bool:



        user = await self.get_user_by_id(user_id)
        return user.role == required_role