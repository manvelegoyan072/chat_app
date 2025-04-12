import redis.asyncio as redis
from fastapi import HTTPException
import os
from datetime import timedelta

class RedisService:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )

    async def add_to_blacklist(self, token: str, expire_minutes: int):



        await self.client.setex(
            name=f"blacklist:{token}",
            time=timedelta(minutes=expire_minutes),
            value="1"
        )

    async def is_blacklisted(self, token: str) -> bool:



        return await self.client.exists(f"blacklist:{token}") > 0

    async def close(self):



        await self.client.aclose()