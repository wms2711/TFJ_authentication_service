"""
Chat Router
==========

Handles all chat-related operations including:
- Retrieving user conversations
- Fetching chat history with specific users
- Real-time communication via WebSocket
- Fallback HTTP-based message sending

Security:
- All endpoints (except WebSocket) require a valid JWT in the `Authorization` header.
- WebSocket connections require token verification during the handshake.

Supported Flows:
----------------
1. Viewing chat list:       GET /chat/conversations
2. Viewing chat history:    GET /chat/conversations/{user_id}
3. Sending messages (HTTP): POST /chat/messages
4. Real-time chat:          WebSocket /chat/ws/{user_id}
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import async_get_db
from app.dependencies import get_current_user
from app.database.models.user import User
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.redis import RedisService
from app.schemas.chat import ChatUser, MessageOut, MessageResponse, MessageCreateHTTP
from utils.logger import init_logger

# Configure logger
logger = init_logger("ChatService")

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

@router.get("/conversations", response_model=List[ChatUser])
async def get_chat_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
    redis: RedisService = Depends(RedisService)
):
    """
    Get all users with whom the current user has existing conversations.

    Flow:
    1. Authenticate current user via JWT.
    2. Query all unique chat partners from messages.
    
    Returns:
        List[ChatUser]: Users the current user has messaged or received messages from.
    """
    # No need cache as chat expects real-time responsiveness, cache might cause information to be the older version
    # chat_service = ChatService(db=db, redis_service=redis)
    chat_service = ChatService(db=db, redis_service=None)
    return await chat_service.get_user_conversations(current_user.id)

@router.get("/conversations/{user_id}", response_model=List[MessageOut])
async def get_chat_history(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Get full chat history between current user and another user.

    Flow:
    1. Authenticate current user.
    2. Query messages where current user is sender or receiver.
    
    Args:
        user_id (int): ID of the other user in the conversation.

    Returns:
        List[MessageOut]: Chronologically ordered message history.
    """
    chat_service = ChatService(db=db, redis_service=None)
    return await chat_service.get_user_messages(current_user.id, user_id)

@router.post("/messages", response_model=MessageResponse)
async def send_message_http(
    message: MessageCreateHTTP,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """
    Send a message via HTTP (as a fallback to WebSocket).

    Flow:
    1. Authenticate sender from JWT.
    2. Accept receiver ID and message content in body.
    3. Save message to database.
    4. Attempt to send via WebSocket (if receiver is connected).

    Args:
        message (MessageCreateHTTP): Contains sender_id, receiver_id, and content.
        current_user (User): Authenticated user from JWT.

    Returns:
        MessageResponse: Includes message object and WebSocket delivery status.
    """
    chat_service = ChatService(db=db, redis_service=None)
    return await chat_service.send_message_http(message, current_user.id)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    db: AsyncSession = Depends(async_get_db)
):
    """
    WebSocket endpoint for real-time chat messaging.

    Flow:
    1. Extract Bearer token from WebSocket headers.
    2. Verify JWT and match `user_id` with token subject.
    3. Register socket connection in internal registry.
    4. Maintain connection and handle real-time message exchange.
    
    Security:
    - Requires `Authorization: Bearer <JWT>` header.
    - Connection will be rejected with code 1008 on failure.

    Args:
        websocket (WebSocket): Active WebSocket connection.
        user_id (int): ID of the user initiating the connection.

    Lifecycle:
    - On connect: Authenticate and register connection.
    - On receive: Handle incoming messages or status.
    - On disconnect: Clean up connection state.
    """
    chat_service = ChatService(db=db, redis_service=None)

    # Extract token
    token = websocket.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("Missing or invalid Authorization header on WebSocket connect")
        return
    token = token[7:]

    # Validate token and user
    auth_service = AuthService(db=db)
    try:
        token_data = auth_service.verify_token(token=token)
        user = await auth_service.get_user(username=token_data.get("sub"))
        if str(user_id) != str(user.id):
            raise ValueError("User ID mismatch with token subject")
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await chat_service.handle_websocket_connection(websocket, user_id)