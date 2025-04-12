from fastapi import FastAPI, Depends, HTTPException, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_db
from app.controllers.chat_controller import router as chat_router
from app.controllers.message_controller import router as message_router
from app.controllers.auth_controller import router as auth_router
from app.services.redis_service import RedisService
from app.middlewares.csrf_middleware import csrf_middleware
from jose import JWTError, jwt
from app.schemas.user import UserRole
import os
from typing import NamedTuple, Optional

app = FastAPI(
    title="Messenger API",
    description="API for a real-time chat application",
    debug=os.getenv("DEBUG_MODE", "False").lower() == "true"
)

app.middleware("http")(csrf_middleware)

app.include_router(chat_router)
app.include_router(message_router)
app.include_router(auth_router)


class CurrentUser(NamedTuple):
    id: int
    role: UserRole


async def get_current_user(
        access_token: Optional[str] = Cookie(None),
        token: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    from app.services.user_service import UserService

    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM = "HS256"

    selected_token = access_token or token
    if selected_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    redis_service = RedisService()
    if await redis_service.is_blacklisted(selected_token):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        payload = jwt.decode(selected_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        if role not in [UserRole.USER, UserRole.ADMIN]:
            raise HTTPException(status_code=401, detail="Invalid role")
        user_service = UserService(db)
        user = await user_service.get_user_by_id(int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return CurrentUser(id=user.id, role=UserRole(role))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.on_event("shutdown")
async def shutdown_event():
    redis_service = RedisService()
    await redis_service.close()


@app.get("/")
async def root():
    return {"message": "Messenger API is running!"}