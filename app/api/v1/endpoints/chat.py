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
from app.services.chat import ChatService, ConnectionManager
from app.schemas.chat import ChatUser, MessageOut, MessageResponse, MessageCreateHTTP

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

manager = ConnectionManager()

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