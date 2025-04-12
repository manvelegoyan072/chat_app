from fastapi import FastAPI, Depends, HTTPException, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_db
from app.controllers.chat_controller import router as chat_router
from app.controllers.message_controller import router as message_router
from app.controllers.auth_controller import router as auth_router
from app.services.redis_service import RedisService
from app.middlewares.csrf_middleware import csrf_middleware
from app.logging_config import setup_logging
from jose import JWTError, jwt
from app.schemas.user import UserRole
from prometheus_fastapi_instrumentator import Instrumentator
import redis.asyncio as redis
import os
from typing import NamedTuple, Optional
import logging
from prometheus_client import Counter
websocket_connections_total = Counter('websocket_connections_total', 'Total WebSocket connections')

app = FastAPI(
    title="Messenger API",
    description="API for a real-time chat application",
    debug=os.getenv("DEBUG_MODE", "False").lower() == "true"
)


Instrumentator().instrument(app).expose(app)

app.middleware("http")(csrf_middleware)

app.include_router(chat_router)
app.include_router(message_router)
app.include_router(auth_router)

redis_pool: redis.ConnectionPool = None
logger = logging.getLogger(__name__)


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
        logger.warning("Authentication attempt without token")
        raise HTTPException(status_code=401, detail="Not authenticated")

    redis_service = RedisService(redis_pool)
    if await redis_service.is_blacklisted(selected_token):
        logger.warning(f"Attempt to use blacklisted token: {selected_token[:10]}...")
        raise HTTPException(status_code=401, detail="Token has been revoked")

    try:
        payload = jwt.decode(selected_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            logger.warning("Invalid token payload")
            raise HTTPException(status_code=401, detail="Invalid token")
        if role not in [UserRole.USER, UserRole.ADMIN]:
            logger.warning(f"Invalid role in token: {role}")
            raise HTTPException(status_code=401, detail="Invalid role")
        user_service = UserService(db)
        user = await user_service.get_user_by_id(int(user_id))
        if user is None:
            logger.warning(f"User not found for ID: {user_id}")
            raise HTTPException(status_code=401, detail="User not found")
        logger.debug(f"Authenticated user: {user_id}, role: {role}")
        return CurrentUser(id=user.id, role=UserRole(role))
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


@app.on_event("startup")
async def startup_event():
    global redis_pool
    redis_pool = RedisService.create_pool()
    setup_logging()
    logger.info("Application started")


@app.on_event("shutdown")
async def shutdown_event():
    global redis_pool
    if redis_pool:
        await RedisService.close_pool(redis_pool)
        redis_pool = None
    logger.info("Application shutdown")


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Messenger API is running!"}