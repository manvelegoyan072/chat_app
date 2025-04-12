import pytest


@pytest.mark.asyncio
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