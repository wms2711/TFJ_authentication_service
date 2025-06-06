import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, func
from fastapi import WebSocket, HTTPException, status, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import ValidationError

from app.services.redis import RedisService
from app.database.models.user import User
from app.database.models.chat import ChatMessage
from app.schemas.chat import ChatUser, MessageOut, MessageCreateHTTP, MessageResponse, WsMessage
from utils.logger import init_logger

# Configure logger
logger_chat = init_logger("ChatService")
logger_ws_connection = init_logger("ConnectionManager")

class ConnectionManager:
    """Manages active WebSocket connections for real-time chat functionality."""
    _instance = None

    def __new__(cls):
        """Singleton pattern implementation ensuring only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_connections = {}
        return cls._instance
    
    def __init__(self):
        """Initialize the connection manager (empty for singleton pattern)."""
        pass

    @property
    def connected_user_ids(self) -> List[int]:
        """
        Get list of currently connected user IDs.
        
        Returns:
            List[int]: User IDs of all currently connected users
        """
        return list(self.active_connections.keys())

    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Register a new WebSocket connection for a user.
        
        Flow:
        1. Accept the WebSocket connection
        2. Add to active_connections dictionary
            - Creates new list if first connection for user
            - Appends to existing list if user already has connections

        Args:
            websocket (WebSocket): The WebSocket connection to register
            user_id (int): ID of the connecting user

        Note:
            - Same user can have multiple active connections (different devices/tabs)
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger_ws_connection.info(f"ADDED new WS connection for user_id={user_id}, connection list: {self.active_connections}"
)
    def disconnect(self, user_id: int, websocket: WebSocket = None):
        """
        Remove a WebSocket connection from active connections.
        
        Behavior:
        - If websocket specified: Remove only that specific connection
            - If last connection for user, remove user entry entirely
        - If no websocket specified: Remove all connections for user

        Args:
            user_id (int): ID of the disconnecting user
            websocket (WebSocket, optional): Specific connection to remove
        """
        if websocket:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:  # No remaining connections
                del self.active_connections[user_id]
        else:
            self.active_connections.pop(user_id, None)
        logger_ws_connection.info(f"DELETE CONNECTION for user={user_id}, connection list: {self.active_connections}")

    async def send_to_user(self, user_id: int, message: WsMessage):
        """
        Deliver a message to all active connections for a user.
        
        Flow:
        1. Check if user has active connections
        2. Attempt delivery to each connection
        3. Clean up failed connections

        Args:
            user_id (int): Recipient user ID
            message (WsMessage): Message to deliver

        Note:
            - Silently handles failed deliveries (removes broken connections)
            - Message will be lost if no active connections exist
        """
        if user_id not in self.active_connections:
            return

        message_data = message.dict()
        disconnected_sockets = []

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(message_data)
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")
                disconnected_sockets.append(websocket)

        # Clean up broken sockets
        for ws in disconnected_sockets:
            self.disconnect(user_id, websocket=ws)

class ChatService:
    """Service for managing chat conversations between users."""

    def __init__(
            self, 
            db: AsyncSession, 
            redis_service: Optional[RedisService] = None
        ):
        """
        Initialize chat service with DB session and optional Redis.

        Args:
            db (AsyncSession): SQLAlchemy async DB session.
            redis_service (Optional[RedisService]): Redis for caching.
        """
        self.db = db
        self.redis = redis_service
        self.manager = ConnectionManager()

    async def get_user_conversations(
            self,
            user_id: int
        ) -> List[ChatUser]:
        """
        Get list of users that the given user has had conversations with.

        Flow:
        1. Try to fetch from Redis cache (if available).
        2. If not cached, query the DB for users involved in chats.
        3. Cache the result for future calls. 
        4. Return list of ChatUser (with online status).

        Args:
            user_id (int): ID of the requesting user.

        Returns:
            List[ChatUser]: Users involved in conversations with online info.

        Raises:
            HTTPException: 500 on unexpected errors.
        """
        cache_key = f"chat:conversations:user:{user_id}"
        try:
            # # Find from cache first
            # if self.redis:
            #     try:
            #         cached = await self.redis.get_cache(cache_key)
            #         if cached:
            #             logger_chat.info(f"Cache hit for user conversations: {user_id}")
            #             return [ChatUser.model_validate_json(user_json) for user_json in json.loads(cached)]
            #     except Exception as e:
            #         logger_chat.warning(f"Redis cache read failed for user {user_id}: {e}")

            # Fetch from db if can't find from cache
            stmt = select(User).join(
                ChatMessage,
                or_(
                    and_(
                        ChatMessage.sender_id == user_id,
                        ChatMessage.receiver_id == User.id
                    ),
                    and_(
                        ChatMessage.receiver_id == user_id,
                        ChatMessage.sender_id == User.id
                    )
                )
            ).where(
                User.id != user_id,  # Exclude self from user list
            ).distinct()
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            logger_chat.info(f"Found {len(users)} conversations for user_id {user_id} from db")
            response = [
                ChatUser(
                    id=user.id,
                    username=user.username,
                    is_online=user.id in self.manager.connected_user_ids
                ) for user in users
            ]

            # # Set to Redis cache
            # if self.redis and response:
            #     try:
            #         await self.redis.set_cache(
            #             cache_key,
            #             json.dumps([u.model_dump_json() for u in response]),
            #             ttl=60  # Cache for 1 minutes
            #         )
            #     except Exception as e:
            #         logger_chat.error(f"Failed to cache chat users for user_id={user_id}: {e}")

            return response

        except Exception as e:
            logger_chat.exception(f"Failed to fetch conversations for user_id={user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user conversations"
            )
    
    async def get_user_messages(
            self,
            user1_id: int,
            user2_id: int
        ) -> List[MessageOut]:
        """
        Fetch all chat messages between two users, ordered chronologically.

        Args:
            user1_id (int): ID of the first user (requesting user).
            user2_id (int): ID of the second user (chat partner).

        Returns:
            List[MessageOut]: All chat messages exchanged between the two users.

        Raises:
            HTTPException:
                - 400 if attempting to chat with self or no messages found.
                - 500 if retrieval fails unexpectedly.
        """
        if user1_id == user2_id:
            logger_chat.warning(f"User {user1_id} attempted to fetch chat with self.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chat (with ownself) found"
            )
        try:
            stmt = select(ChatMessage).where(
                or_(
                    and_(
                        ChatMessage.sender_id == user1_id,
                        ChatMessage.receiver_id == user2_id
                    ),
                    and_(
                        ChatMessage.sender_id == user2_id,
                        ChatMessage.receiver_id == user1_id
                    )
                )
            ).order_by(ChatMessage.sent_at.asc())
            result = await self.db.execute(stmt)
            messages = result.scalars().all()

            if not messages:
                logger_chat.info(f"No messages found between user {user1_id} and user {user2_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No chat history found with this user"
                )
            
            logger_chat.info(f"Retrieved {len(messages)} messages between user {user1_id} and user {user2_id}")
            return [MessageOut.model_validate(msg) for msg in messages]
        
        except HTTPException:
            raise
        except Exception as e:
            logger_chat.exception(f"Error retrieving messages between user {user1_id} and user {user2_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve chat messages."
            )
    
    async def save_message(
            self,
            sender_id: int,
            receiver_id: int,
            content: str
        ) -> ChatMessage:
        """
        Save a new chat message between two users.

        Flow:
        1. Create a ChatMessage object with sender, receiver, and content.
        2. Persist it in the database.
        3. Refresh the instance and return it.

        Args:
            sender_id (int): ID of the sender.
            receiver_id (int): ID of the receiver.
            content (str): Message content.

        Returns:
            MessageOut: Serialized response of the saved message.

        Raises:
            HTTPException:
                - 500 if message saving fails.
        """
        try:
            message = ChatMessage(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content,
                sent_at=datetime.utcnow()
            )
            self.db.add(message)
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger_chat.error(f"DB commit failed while saving message: {str(db_exc)}")
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(message)

            if not message.id:
                raise ValueError("Failed to retrieve message ID after insert")
            logger_chat.info(f"Message saved: {sender_id=} -> {receiver_id=}, id={message.id}")
            return message
        
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger_chat.exception(f"Failed to save message from {sender_id} to {receiver_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message."
            )
    
    async def send_message_http(
            self,
            message: MessageCreateHTTP,
            user_id: int
        ) -> MessageResponse:
        """
        Send a direct message from one user to another. Handles database persistence
        and attempts to deliver message in real-time over WebSocket.

        Args:
            message (MessageCreateHTTP): Payload containing sender_id, receiver_id, and content.
            user_id (int): Authenticated user making the request.

        Returns:
            MessageResponse: Contains the message object and WebSocket delivery status.

        Raises:
            HTTPException:
                - 403 if sender_id mismatch or sending to self.
                - 404 if receiver does not exist.
                - 500 on unexpected errors.
        """
        # Check sender
        if message.sender_id != user_id:
            logger_chat.error(f"User {user_id} tried to send message as {message.sender_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send messages as another user"
            )
        
        # Check sender and receiver are the same
        if message.sender_id == message.receiver_id:
            logger_chat.error(f"User {user_id} attempted to message themselves")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send messages to yourself"
            )
        
        try:
            # Check receiver user id exist
            result = await self.db.execute(select(User).where(User.id == message.receiver_id))
            receiver = result.scalars().first()
            if not receiver:
                logger_chat.error(f"Receiver not found: user_id={message.receiver_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Receiver not found"
                )
        
            # Save message to database
            saved_msg = await self.save_message(
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                content=message.content
            )

            # Attempt real-time WebSocket delivery
            is_ws_connected = False
            if message.receiver_id in self.manager.connected_user_ids:
                try:
                    message_out = MessageOut.model_validate(saved_msg).dict()
                    ws_message = WsMessage(
                        type="message",
                        data=message_out
                    )
                    await self.manager.send_to_user(
                        message.receiver_id,
                        ws_message
                    )
                    is_ws_connected = True
                    logger_chat.info(f"Delivered message via WS to user {message.receiver_id}")
                except Exception as ws_exc:
                    # WebSocket failed but we still have the message in DB
                    logger_chat.warning(f"WebSocket delivery failed for user {message.receiver_id}: {str(ws_exc)}")
                    pass

            return MessageResponse(
                success=True,
                message=MessageOut.model_validate(saved_msg),
                is_ws_connected=is_ws_connected
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger_chat.exception(f"Unexpected error during message send: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message"
            )

    async def handle_websocket_connection(self, websocket: WebSocket, user_id: int):
        """
        Manage the WebSocket connection lifecycle.

        Args:
            websocket (WebSocket): WebSocket connection instance.
            user_id (int): ID of the authenticated user.
        """
        await self.manager.connect(websocket, user_id)
        logger_chat.info(f"WebSocket connected for user_id={user_id}")

        try:
            while True:
                try:
                    await self._handle_websocket_message(websocket, user_id)
                except HTTPException as e:
                    # Send error message to client before closing
                    error_msg = WsMessage(
                        type="error",
                        data={"detail": e.detail}
                    )
                    await websocket.send_json(error_msg.dict())
                    logger_chat.warning(f"WebSocket error for user_id={user_id}: {e.detail}")
                    break
                except WebSocketDisconnect:
                    # Normal disconnection
                    break
                except Exception as e:
                    logger_chat.exception(f"Unexpected error in WebSocket for user_id={user_id}: {e}")
                    break

        except Exception as e:
            logger_chat.exception(f"Connection error for user_id={user_id}: {e}")
        finally:
            self.manager.disconnect(user_id, websocket)
            logger_chat.info(f"WebSocket disconnected for user_id={user_id}")

    async def _handle_websocket_message(self, websocket: WebSocket, user_id: int):
        """
        Handle a message received over WebSocket.

        Args:
            websocket (WebSocket): WebSocket connection instance.
            user_id (int): ID of the message sender.
        """
        try:
            data = await websocket.receive_json()
            message = WsMessage(**data)
        
            if message.type == "message":
                await self._handle_chat_message(user_id, message.data)
            elif message.type == "read_receipt":
                await self._handle_read_receipt(user_id, message.data)
            else:
                logger_chat.warning(f"Unknown message type received from user_id={user_id}: {message.type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unknown message type"
                )

        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format"
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message format"
            )

    async def _handle_chat_message(self, sender_id: int, message_data: dict):
        """
        Handle chat message and forward to recipient if online.

        Args:
            sender_id (int): ID of the user sending the message.
            message_data (Dict): Data dictionary containing content and receiver_id.
        """
        receiver_id = message_data.get("receiver_id")
        content = message_data.get("content")

        if not receiver_id or not content:
            logger_chat.warning(f"Incomplete message from user_id={sender_id}: {message_data}")
            return

        if sender_id == receiver_id:
            logger_chat.warning(f"User {sender_id} attempted to message themselves. Ignored.")
            return
        
        try:
            # Check receiver user id exist
            result = await self.db.execute(select(User).where(User.id == receiver_id))
            receiver = result.scalars().first()
            if not receiver:
                logger_chat.warning(f"Receiver not found: user_id={receiver_id}")
                return
            
            # Save message to database
            saved_msg = await self.save_message(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=content
            )
            
            # Serialize message
            message_out = MessageOut.from_db_model(saved_msg)
            ws_message = WsMessage(
                type="message",
                data=jsonable_encoder(message_out.model_dump())
            )
        
            # Send confirmation to sender (Message echo)
            await self.manager.send_to_user(sender_id, ws_message)
        
            # Send to receiver if online
            if receiver_id in self.manager.connected_user_ids:
                await self.manager.send_to_user(receiver_id,ws_message)
                logger_chat.info(f"Message from user_id={sender_id} delivered to user_id={receiver_id} via WebSocket.")
            else:
                logger_chat.info(f"Receiver user_id={receiver_id} not connected. Message stored only.")
                
        except Exception as e:
            logger_chat.exception(f"Failed to handle chat message from user_id={sender_id} to user_id={receiver_id}: {e}")

    async def _handle_read_receipt(self, receiver_id: int, receipt_data: dict):
        """Process a read receipt received via WebSocket"""
        await self.mark_messages_as_read(
            sender_id=receipt_data["sender_id"],
            receiver_id=receiver_id
        )

