from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.services.redis_service import RedisService
from app.services.csrf_service import CSRFService
from app.schemas.user import UserCreate, UserResponse
from app.config import get_db
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "False").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    logger.info(f"Registering user with email: {user_data.email}")
    try:
        user = await user_service.create_user(user_data)
        logger.debug(f"User registered successfully: {user.id}")
        return user
    except HTTPException as e:
        logger.error(f"Registration failed: {str(e.detail)}")
        raise


@router.post("/token")
async def login_for_access_token(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    logger.info(f"Login attempt for user: {form_data.username}")
    user = await user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
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

    csrf_service = CSRFService()
    csrf_token = csrf_service.generate_csrf_token(str(user.id))

    logger.debug(f"User {user.id} logged in, access token issued")
    return {
        "refresh_token": refresh_token,
        "csrf_token": csrf_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
async def refresh_access_token(
        response: Response,
        refresh_token: str,
        db: AsyncSession = Depends(get_db)
):
    user_service = UserService(db)
    logger.info("Refresh token request")
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
        csrf_service = CSRFService()
        csrf_token = csrf_service.generate_csrf_token(str(user.id))
        logger.debug(f"Access token refreshed for user: {user.id}")
        return {
            "token_type": "bearer",
            "csrf_token": csrf_token
        }
    except HTTPException as e:
        logger.error(f"Refresh token failed: {str(e.detail)}")
        raise


@router.post("/logout")
async def logout(
        response: Response,
        access_token: str = Cookie(None),
        refresh_token: str = None,
        csrf_token: str = Depends(lambda x: x.headers.get("X-CSRF-Token")),
        db: AsyncSession = Depends(get_db)
):
    logger.info("Logout request")
    if not access_token:
        logger.warning("Logout attempt without access token")
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        csrf_service = CSRFService()
        if not csrf_service.verify_csrf_token(user_id, csrf_token):
            logger.warning(f"Invalid CSRF token for user: {user_id}")
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    except JWTError:
        logger.error("Invalid access token during logout")
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.main import redis_pool
    redis_service = RedisService(redis_pool)
    if access_token:
        await redis_service.add_to_blacklist(access_token, ACCESS_TOKEN_EXPIRE_MINUTES)
        logger.debug(f"Access token blacklisted for user: {user_id}")

    if refresh_token:
        user_service = UserService(db)
        try:
            await user_service.delete_refresh_token(refresh_token)
            logger.debug(f"Refresh token deleted for user: {user_id}")
        except HTTPException:
            logger.warning(f"Attempt to delete invalid refresh token")

    response.delete_cookie(key="access_token")
    logger.info(f"User {user_id} logged out successfully")
    return {"message": "Logged out successfully"}


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt