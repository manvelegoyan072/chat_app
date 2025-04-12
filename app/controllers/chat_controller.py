from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.schemas.chat import ChatCreate, ChatResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.config import get_db
from app.main import get_current_user
from typing import Dict, List
import json

router = APIRouter(prefix="/chats", tags=["Chats"])
websocket_connections: Dict[int, List[WebSocket]] = {}  # Хранит соединения по chat_id

@router.post("/", response_model=ChatResponse)
async def create_personal_chat(
        user1_id: int,
        user2_id: int,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if current_user.id not in [user1_id, user2_id]:
        raise HTTPException(status_code=403, detail="Not authorized to create this chat")
    chat_service = ChatService(db)
    return await chat_service.create_personal_chat(user1_id, user2_id)

@router.post("/group", response_model=ChatResponse)
async def create_group_chat(
        chat_data: ChatCreate,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    chat_service = ChatService(db)
    return await chat_service.create_group_chat(chat_data, current_user.id)

@router.websocket("/{chat_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        chat_id: int,
        token: str,  # JWT-токен как query-параметр
        db: AsyncSession = Depends(get_db)
):
    try:
        current_user = await get_current_user(token=token, db=db)
    except HTTPException:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()

    # Проверка доступа к чату
    chat_service = ChatService(db)
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        await websocket.close(code=1008, reason="Chat not found")
        return
    if not await chat_service.chat_repo.is_participant(chat_id, current_user.id):
        await websocket.close(code=1008, reason="User not in chat")
        return

    # Добавление WebSocket в список соединений
    if chat_id not in websocket_connections:
        websocket_connections[chat_id] = []
    websocket_connections[chat_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            # Отправка сообщения
            if message_data.get("type") == "message":
                message_service = MessageService(db)
                message = MessageCreate(
                    chat_id=chat_id,
                    text=message_data.get("text", "")
                )
                message_uuid = message_data.get("uuid")
                if not message_uuid:
                    await websocket.send_json({"type": "error", "detail": "UUID required"})
                    continue
                try:
                    saved_message = await message_service.send_message(message, current_user.id, message_uuid)
                    # Рассылка сообщения всем участникам чата
                    for ws in websocket_connections.get(chat_id, []):
                        await ws.send_json({
                            "type": "message",
                            "message": MessageResponse.model_validate(saved_message).model_dump()
                        })
                except HTTPException as e:
                    await websocket.send_json({"type": "error", "detail": str(e.detail)})

            # Отметка сообщения как прочитанного
            elif message_data.get("type") == "read":
                message_service = MessageService(db)
                message_id = message_data.get("message_id")
                if not message_id:
                    await websocket.send_json({"type": "error", "detail": "Message ID required"})
                    continue
                try:
                    await message_service.mark_message_as_read(message_id, current_user.id)
                    for ws in websocket_connections.get(chat_id, []):
                        await ws.send_json({
                            "type": "read",
                            "message_id": message_id
                        })
                except HTTPException as e:
                    await websocket.send_json({"type": "error", "detail": str(e.detail)})

    except WebSocketDisconnect:
        websocket_connections[chat_id].remove(websocket)
        if not websocket_connections[chat_id]:
            del websocket_connections[chat_id]