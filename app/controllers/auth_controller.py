from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.services.redis_service import RedisService
from app.schemas.user import UserCreate, UserResponse
from app.config import get_db
from jose import jwt
from datetime import datetime, timedelta
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    return await user_service.create_user(user_data)


@router.post("/token")
async def login_for_access_token(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )
    refresh_token = await user_service.create_refresh_token(user.id)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=int(access_token_expires.total_seconds())
    )

    return {
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
async def refresh_access_token(
        response: Response,
        refresh_token: str,
        db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    try:
        refresh_token_obj = await user_service.get_refresh_token(refresh_token)
        user = await user_service.get_user_by_id(refresh_token_obj.user_id)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=access_token_expires
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=int(access_token_expires.total_seconds())
        )
        return {"token_type": "bearer"}
    except HTTPException as e:
        raise HTTPException(status_code=401, detail=str(e.detail))


@router.post("/logout")
async def logout(
        response: Response,
        access_token: str = Cookie(None),
        refresh_token: str = None,
        db: AsyncSession = Depends(get_db)
):
    redis_service = RedisService()


    if access_token:
        await redis_service.add_to_blacklist(access_token, ACCESS_TOKEN_EXPIRE_MINUTES)


    if refresh_token:
        user_service = UserService(db)
        try:
            await user_service.delete_refresh_token(refresh_token)
        except HTTPException:
            pass

    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt