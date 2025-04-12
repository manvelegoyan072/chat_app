import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.models import Base
from app.services.chat_service import ChatService
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from httpx import AsyncClient

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
async def users(db_session: AsyncSession):
    user_service = UserService(db_session)
    user1 = await user_service.create_user(UserCreate(name="User1", email="user1@test.com", password="pass"))
    user2 = await user_service.create_user(UserCreate(name="User2", email="user2@test.com", password="pass"))
    return user1, user2

@pytest_asyncio.fixture
async def token(async_client, users):
    response = await async_client.post(
        "/auth/token",
        data={"username": "user1@test.com", "password": "pass"}
    )
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_create_personal_chat(db_session: AsyncSession, users, async_client, token):
    user1, user2 = users
    response = await async_client.post(
        "/chats/",
        json={"user1_id": user1.id, "user2_id": user2.id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    chat = response.json()
    assert chat["type"] == "personal"

@pytest.mark.asyncio
async def test_create_group_chat(db_session: AsyncSession, users, async_client, token):
    response = await async_client.post(
        "/chats/group",
        json={"name": "Test Group", "creator_id": users[0].id},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    chat = response.json()
    assert chat["type"] == "group"
    assert chat["name"] == "Test Group"