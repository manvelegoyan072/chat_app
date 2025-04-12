import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.models import Base
from app.schemas.user import UserCreate
import redis.asyncio as redis
from dotenv import load_dotenv
import os


load_dotenv(".env.test")


@pytest_asyncio.fixture
async def db_session():

    database_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def redis_client():
    pool = redis.ConnectionPool(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
        max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    )
    client = redis.Redis(connection_pool=pool)
    yield client
    await client.aclose()
    await pool.aclose()


@pytest_asyncio.fixture
def client():
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    return AsyncClient(app=app, base_url="http://test")


@pytest_asyncio.fixture
async def user(db_session: AsyncSession):
    from app.services.user_service import UserService
    user_service = UserService(db_session)
    user = await user_service.create_user(
        UserCreate(name="Test User", email="test@test.com", password="password")
    )
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    from app.services.user_service import UserService
    user_service = UserService(db_session)
    user = await user_service.create_user(
        UserCreate(name="Admin User", email="admin@test.com", password="password", role="admin")
    )
    return user