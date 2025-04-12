import pytest


@pytest.mark.asyncio
async def test_create_user_with_role(db_session):
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