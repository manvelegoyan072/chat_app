import pytest
import logging


@pytest.mark.asyncio
async def test_logging_on_failed_login(async_client, caplog):
    caplog.set_level(logging.WARNING)
    response = await async_client.post(
        "/auth/token",
        data={"username": "wrong@test.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert "Failed login attempt for user: wrong@test.com" in caplog.text