from fastapi import HTTPException, Request
from app.services.csrf_service import CSRFService
from app.services.redis_service import RedisService
from jose import jwt, JWTError
import os


async def csrf_middleware(request: Request, call_next):

    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return await call_next(request)


    if request.url.path in {"/auth/token", "/auth/refresh"}:
        return await call_next(request)

    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")


    redis_service = RedisService()
    if await redis_service.is_blacklisted(access_token):
        raise HTTPException(status_code=401, detail="Token has been revoked")


    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    try:
        payload = jwt.decode(
            access_token,
            os.getenv("SECRET_KEY", "your-secret-key"),
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        csrf_service = CSRFService()
        if not csrf_service.verify_csrf_token(user_id, csrf_token):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return await call_next(request)