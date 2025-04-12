import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.schemas.message import MessageCreate
from httpx import AsyncClient
import uuid


@pytest.mark.asyncio
async def test_send_message(db_session: AsyncSession, users, async_client, token):
    user1, user2 = users
    chat_service = ChatService(db_session)
    chat = await chat_service.create_personal_chat(user1.id, user2.id)

    message_data = {"chat_id": chat.id, "text": "Hello!", "uuid": str(uuid.uuid4())}
    response = await async_client.post(
        "/messages/",  # Временный эндпоинт для теста, в реальном проекте через WebSocket
        json=message_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    message = response.json()
    assert message["text"] == "Hello!"
    assert message["chat_id"] == chat.id


@pytest.mark.asyncio
async def test_get_message_history(db_session: AsyncSession, users, async_client, token):
    user1, user2 = users
    chat_service = ChatService(db_session)
    message_service = MessageService(db_session)

    chat = await chat_service.create_personal_chat(user1.id, user2.id)
    for i in range(3):
        message_data = MessageCreate(chat_id=chat.id, text=f"Msg {i}")
        await message_service.send_message(message_data, user1.id, str(uuid.uuid4()))

    response = await async_client.get(
        f"/history/{chat.id}?limit=2&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 2
    assert history[0]["text"] == "Msg 0"