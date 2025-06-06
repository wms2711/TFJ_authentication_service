"""
Chat Router
==========

Handles all chat-related operations including:
- Viewing all chats for the user
- Viewing specific chat
- Websocket connection for the chat
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import async_get_db
from app.dependencies import get_current_user
from app.database.models.user import User
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.schemas.chat import ChatUser, MessageOut, MessageResponse, MessageCreateHTTP

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

@router.get("/conversations", response_model=List[ChatUser])
async def get_chat_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Get all users with whom current user has chatted"""
    chat_service = ChatService(db)
    return await chat_service.get_user_conversations(current_user.id)

@router.get("/conversations/{user_id}", response_model=List[MessageOut])
async def get_chat_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Get message history between current user and another user"""
    chat_service = ChatService(db)
    return await chat_service.get_user_messages(current_user.id, user_id)

@router.post("/messages", response_model=MessageResponse)
async def send_message_http(
    message: MessageCreateHTTP,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """HTTP fallback for sending messages when WebSocket is not available"""
    chat_service = ChatService(db)
    return await chat_service.send_message_http(message, current_user.id)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    db: AsyncSession = Depends(async_get_db)
):
    """WebSocket endpoint for real-time chat communication"""
    chat_service = ChatService(db=db)

    # Verify token
    token = websocket.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        await websocket.close(code=1008)
        return
    token = token[7:]
    auth_service = AuthService(db=db)
    verify_user = auth_service.verify_token(token=token)
    if not verify_user:
        await websocket.close(code=1008)
        return
    
    # Verify user
    user = await auth_service.get_user(username=verify_user.get("sub"))
    if str(user_id) != str(user.id):
        await websocket.close(code=1008)
        return

    await chat_service.handle_websocket_connection(websocket, user_id)