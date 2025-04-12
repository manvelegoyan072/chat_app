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
async def redis_client():
    pool = redis.ConnectionPool(
        host="localhost",
        port=6379,
        decode_responses=True,
        max_connections=10
    )
    client = redis.Redis(connection_pool=pool)
    yield client
    await client.aclose()
    await pool.aclose()


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


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    from app.services.user_service import UserService
    user_service = UserService(db_session)
    user = await user_service.create_user(
        UserCreate(name="Admin User", email="admin@test.com", password="password", role="admin")
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
    assert "access_token" in response.cookies
    assert "refresh_token" in data
    assert "csrf_token" in data
    assert data["token_type"] == "bearer"


@pytest_mark.asyncio
async def test_refresh_token(async_client, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in refresh_response.cookies
    assert "csrf_token" in data
    assert data["token_type"] == "bearer"
    assert "refresh_token" not in data


@pytest_mark.asyncio
async def test_refresh_with_invalid_token(async_client):
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


@pytest_mark.asyncio
async def test_create_user_with_role(async_client, db_session):
    from app.services.user_service import UserService
    user_service = UserService(db_session)
    user = await user_service.create_user(
        UserCreate(name="Test User", email="test2@test.com", password="password", role="user")
    )
    assert user.role == "user"
    admin = await user_service.create_user(
        UserCreate(name="Admin User", email="admin2@test.com", password="password", role="admin")
    )
    assert admin.role == "admin"


@pytest_mark.asyncio
async def test_group_add_participant_as_admin(async_client, admin_user, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "admin@test.com", "password": "password"}
    )
    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    from app.services.chat_service import ChatService
    from app.services.group_service import GroupService
    db = next(get_db())
    chat_service = ChatService(db)
    group_service = GroupService(db)
    chat = await chat_service.create_group_chat(ChatCreate(name="Test Group"), admin_user.id)
    group = await group_service.create_group(chat.id, admin_user.id, "Test Group")

    response = await async_client.post(
        f"/chats/group/{group.id}/participants",
        json={"user_id": user.id},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200
    assert response.json()["message"] == f"User {user.id} added to group {group.id}"


@pytest_mark.asyncio
async def test_group_add_participant_without_csrf(async_client, admin_user, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "admin@test.com", "password": "password"}
    )
    assert login_response.status_code == 200

    from app.services.chat_service import ChatService
    from app.services.group_service import GroupService
    db = next(get_db())
    chat_service = ChatService(db)
    group_service = GroupService(db)
    chat = await chat_service.create_group_chat(ChatCreate(name="Test Group"), admin_user.id)
    group = await group_service.create_group(chat.id, admin_user.id, "Test Group")

    response = await async_client.post(
        f"/chats/group/{group.id}/participants",
        json={"user_id": user.id}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"


@pytest_mark.asyncio
async def test_group_add_participant_as_non_admin(async_client, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    response = await async_client.post(
        f"/chats/group/1/participants",
        json={"user_id": user.id},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Only group creator or admin can add participants"


@pytest_mark.asyncio
async def test_access_protected_endpoint_with_cookie(async_client, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    response = await async_client.post(
        "/chats/",
        json={"user1_id": user.id, "user2_id": user.id + 1},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert response.status_code == 200


@pytest_mark.asyncio
async def test_logout(async_client, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    refresh_token = login_response.json()["refresh_token"]
    csrf_token = login_response.json()["csrf_token"]

    logout_response = await async_client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert logout_response.status_code == 200
    assert "access_token" not in logout_response.cookies
    assert logout_response.json()["message"] == "Logged out successfully"


@pytest_mark.asyncio
async def test_blacklist_token(async_client, user, redis_client):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "test@test.com", "password": "password"}
    )
    assert login_response.status_code == 200
    access_token = login_response.cookies["access_token"]
    refresh_token = login_response.json()["refresh_token"]
    csrf_token = login_response.json()["csrf_token"]

    chat_response = await async_client.post(
        "/chats/",
        json={"user1_id": user.id, "user2_id": user.id + 1},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert chat_response.status_code == 200

    logout_response = await async_client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert logout_response.status_code == 200

    async_client.cookies.set("access_token", access_token)
    chat_response = await async_client.post(
        "/chats/",
        json={"user1_id": user.id, "user2_id": user.id + 1},
        headers={"X-CSRF-Token": csrf_token}
    )
    assert chat_response.status_code == 401
    assert chat_response.json()["detail"] == "Token has been revoked"