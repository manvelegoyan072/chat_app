from fastapi import HTTPException, Request
from app.services.csrf_service import CSRFService
from app.services.redis_service import RedisService
from jose import jwt, JWTError
import os
import logging

logger = logging.getLogger(__name__)


async def csrf_middleware(request: Request, call_next):
    logger.debug(f"Processing request: {request.method} {request.url.path}")
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        logger.debug("Skipping CSRF check for safe method")
        return await call_next(request)

    if request.url.path in {"/auth/token", "/auth/refresh"}:
        logger.debug("Skipping CSRF check for auth endpoints")
        return await call_next(request)

    access_token = request.cookies.get("access_token")
    if not access_token:
        logger.warning("No access token in request")
        raise HTTPException(status_code=401, detail="Not authenticated")

    from app.main import redis_pool
    redis_service = RedisService(redis_pool)
    if await redis_service.is_blacklisted(access_token):
        logger.warning(f"Blacklisted token used: {access_token[:10]}...")
        raise HTTPException(status_code=401, detail="Token has been revoked")

    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        logger.warning("CSRF token missing")
        raise HTTPException(status_code=403, detail="CSRF token missing")

    try:
        payload = jwt.decode(
            access_token,
            os.getenv("SECRET_KEY", "your-secret-key"),
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("No user_id in token payload")
            raise HTTPException(status_code=401, detail="Invalid token")

        csrf_service = CSRFService()
        if not csrf_service.verify_csrf_token(user_id, csrf_token):
            logger.warning(f"Invalid CSRF token for user: {user_id}")
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        logger.debug(f"CSRF check passed for user: {user_id}")
    except JWTError:
        logger.error("JWT decode error in CSRF middleware")
        raise HTTPException(status_code=401, detail="Invalid token")

    response = await call_next(request)
    return response