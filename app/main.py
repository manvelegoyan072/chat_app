from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_db, init_db
from app.controllers.chat_controller import router as chat_router
from app.controllers.message_controller import router as message_router
from app.controllers.auth_controller import router as auth_router
from jose import JWTError, jwt
import os

app = FastAPI(
    title="Messenger API",
    description="API for a real-time chat application",
    debug=os.getenv("DEBUG_MODE", "False").lower() == "true"
)

app.include_router(chat_router)
app.include_router(message_router)
app.include_router(auth_router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    from app.services.user_service import UserService

    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM = "HS256"

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_service = UserService(db)
        user = await user_service.get_user_by_id(int(user_id))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.on_event("startup")
async def startup_event():
    if os.getenv("ENVIRONMENT", "development") == "development":
        await init_db()


@app.get("/")
async def root():
    return {"message": "Messenger API is running!"}