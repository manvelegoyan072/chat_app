import pytest


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(async_client):
    response = await async_client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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