import pytest

from app.schemas.chat import ChatCreate


@pytest.mark.asyncio
async def test_group_add_participant_as_admin(async_client, admin_user, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "admin@test.com", "password": "password"}
    )
    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    from app.services.chat_service import ChatService
    from app.services.group_service import GroupService
    from app.config import get_db
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


@pytest.mark.asyncio
async def test_group_add_participant_without_csrf(async_client, admin_user, user):
    login_response = await async_client.post(
        "/auth/token",
        data={"username": "admin@test.com", "password": "password"}
    )
    assert login_response.status_code == 200

    from app.services.chat_service import ChatService
    from app.services.group_service import GroupService
    from app.config import get_db
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


@pytest.mark.asyncio
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