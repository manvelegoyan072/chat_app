import redis.asyncio as redis
from fastapi import HTTPException
import os
from datetime import timedelta

class RedisService:
    def __init__(self, pool: redis.ConnectionPool):
        self.pool = pool
        self.client = redis.Redis(connection_pool=pool)

    async def add_to_blacklist(self, token: str, expire_minutes: int):
        """
        Добавляет токен в чёрный список с TTL.
        """
        await self.client.setex(
            name=f"blacklist:{token}",
            time=timedelta(minutes=expire_minutes),
            value="1"
        )

    async def is_blacklisted(self, token: str) -> bool:
        """
        Проверяет, находится ли токен в чёрном списке.
        """
        return await self.client.exists(f"blacklist:{token}") > 0

    @staticmethod
    async def close_pool(pool: redis.ConnectionPool):
        """
        Закрывает пул соединений.
        """
        await pool.aclose()

    @staticmethod
    def create_pool() -> redis.ConnectionPool:
        """
        Создаёт пул соединений Redis.
        """
        return redis.ConnectionPool(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
            decode_responses=True
        )