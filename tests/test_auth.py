import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.models import Base
from app.schemas.user import UserCreate


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
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


@pytest_mark.asyncio
async def test_login_with_refresh_token(async_client, user):
    response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest_mark.asyncio
async def test_refresh_token(async_client, user):
    # Получаем токены
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    refresh_token = login_response.json()["refresh_token"]

    # Обновляем access-токен
    refresh_response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" not in data  # Новый refresh-токен не выдаётся


@pytest_mark.asyncio
async def test_refresh_with_invalid_token(async_client):
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"