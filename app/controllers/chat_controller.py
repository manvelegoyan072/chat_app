from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.services.group_service import GroupService
from app.schemas.chat import ChatCreate, ChatResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.config import get_db
from app.main import get_current_user, CurrentUser
from typing import Dict, List
import json
import logging

router = APIRouter(prefix="/chats", tags=["Chats"])
websocket_connections: Dict[int, List[WebSocket]] = {}
logger = logging.getLogger(__name__)

@router.post("/", response_model=ChatResponse)
async def create_personal_chat(
        user1_id: int,
        user2_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"Creating personal chat between users: {user1_id}, {user2_id}")
    if current_user.id not in [user1_id, user2_id]:
        logger.warning(f"User {current_user.id} not authorized to create chat")
        raise HTTPException(status_code=403, detail="Not authorized to create this chat")
    chat_service = ChatService(db)
    chat = await chat_service.create_personal_chat(user1_id, user2_id)
    logger.debug(f"Personal chat created: {chat.id}")
    return chat

@router.post("/group", response_model=ChatResponse)
async def create_group_chat(
        chat_data: ChatCreate,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"Creating group chat: {chat_data.name}")
    chat_service = ChatService(db)
    chat = await chat_service.create_group_chat(chat_data, current_user.id)
    logger.debug(f"Group chat created: {chat.id}")
    return chat

@router.post("/group/{group_id}/participants")
async def add_group_participant(
        group_id: int,
        user_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"Adding user {user_id} to group {group_id}")
    group_service = GroupService(db)
    try:
        await group_service.add_participant(group_id, user_id, current_user.id)
        logger.debug(f"User {user_id} added to group {group_id}")
        return {"message": f"User {user_id} added to group {group_id}"}
    except HTTPException as e:
        logger.error(f"Failed to add user to group: {str(e.detail)}")
        raise

@router.delete("/group/{group_id}/participants/{user_id}")
async def remove_group_participant(
        group_id: int,
        user_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"Removing user {user_id} from group {group_id}")
    group_service = GroupService(db)
    try:
        await group_service.remove_participant(group_id, user_id, current_user.id)
        logger.debug(f"User {user_id} removed from group {group_id}")
        return {"message": f"User {user_id} removed from group {group_id}"}
    except HTTPException as e:
        logger.error(f"Failed to remove user from group: {str(e.detail)}")
        raise

@router.websocket("/{chat_id}")
async def websocket_endpoint(
        websocket: WebSocket,
        chat_id: int,
        token: str,
        db: AsyncSession = Depends(get_db)
):
    logger.info(f"WebSocket connection attempt for chat: {chat_id}")
    try:
        current_user = await get_current_user(token=token, db=db)
    except HTTPException:
        logger.warning("Invalid token for WebSocket connection")
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()
    logger.debug(f"WebSocket connected for user: {current_user.id}, chat: {chat_id}")

    chat_service = ChatService(db)
    chat = await chat_service.get_chat_by_id(chat_id)
    if not chat:
        logger.warning(f"Chat not found: {chat_id}")
        await websocket.close(code=1008, reason="Chat not found")
        return
    if not await chat_service.chat_repo.is_participant(chat_id, current_user.id):
        logger.warning(f"User {current_user.id} not in chat: {chat_id}")
        await websocket.close(code=1008, reason="User not in chat")
        return

    if chat_id not in websocket_connections:
        websocket_connections[chat_id] = []
    websocket_connections[chat_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in WebSocket message")
                await websocket.send_json({"type": "error", "detail": "Invalid JSON"})
                continue

            if message_data.get("type") == "message":
                logger.info(f"New message in chat {chat_id} from user {current_user.id}")
                message_service = MessageService(db)
                message = MessageCreate(
                    chat_id=chat_id,
                    text=message_data.get("text", "")
                )
                message_uuid = message_data.get("uuid")
                if not message_uuid:
                    logger.warning("Message UUID missing")
                    await websocket.send_json({"type": "error", "detail": "UUID required"})
                    continue
                try:
                    saved_message = await message_service.send_message(message, current_user.id, message_uuid)
                    logger.debug(f"Message sent: {saved_message.id}")
                    for ws in websocket_connections.get(chat_id, []):
                        await ws.send_json({
                            "type": "message",
                            "message": MessageResponse.model_validate(saved_message).model_dump()
                        })
                except HTTPException as e:
                    logger.error(f"Failed to send message: {str(e.detail)}")
                    await websocket.send_json({"type": "error", "detail": str(e.detail)})

            elif message_data.get("type") == "read":
                logger.info(f"Marking message as read in chat {chat_id}")
                message_service = MessageService(db)
                message_id = message_data.get("message_id")
                if not message_id:
                    logger.warning("Message ID missing for read action")
                    await websocket.send_json({"type": "error", "detail": "Message ID required"})
                    continue
                try:
                    await message_service.mark_message_as_read(message_id, current_user.id)
                    logger.debug(f"Message {message_id} marked as read")
                    for ws in websocket_connections.get(chat_id, []):
                        await ws.send_json({
                            "type": "read",
                            "message_id": message_id
                        })
                except HTTPException as e:
                    logger.error(f"Failed to mark message as read: {str(e.detail)}")
                    await websocket.send_json({"type": "error", "detail": str(e.detail)})

    except WebSocketDisconnect:
        websocket_connections[chat_id].remove(websocket)
        if not websocket_connections[chat_id]:
            del websocket_connections[chat_id]
        logger.info(f"WebSocket disconnected for chat: {chat_id}")