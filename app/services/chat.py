from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, func
from fastapi import WebSocket, HTTPException, status
from datetime import datetime
from typing import Dict, List

from app.database.models.user import User
from app.database.models.chat import ChatMessage
from app.schemas.chat import ChatUser, MessageOut, MessageCreateHTTP, MessageResponse, WsMessage

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    @property
    def connected_user_ids(self) -> List[int]:
        return list(self.active_connections.keys())

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_conversations(
            self,
            user_id: int
        ) -> List[ChatUser]:
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
        ).distinct()
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        return [
            ChatUser(
                id=user.id,
                username=user.username,
                is_online=user.id in ConnectionManager().connected_user_ids
            )
            for user in users
        ]
    
    async def get_user_messages(
            self,
            user1_id: int,
            user2_id: int
        ) -> List[MessageOut]:
        if user1_id == user2_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chat (with ownself) found"
            )
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chat history found with this user"
            )

        return [MessageOut.model_validate(msg) for msg in messages]
    
    async def save_message(
            self,
            sender_id: int,
            receiver_id: int,
            content: str
        ) -> ChatMessage:
        message = ChatMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            sent_at=datetime.utcnow()
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def send_message_http(
            self,
            message: MessageCreateHTTP,
            user_id: int
        ) -> MessageResponse:
        # Check sender and current user are the same
        if message.sender_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send messages as another user"
            )
        
        if message.sender_id == message.receiver_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot send messages to yourself"
            )
        
        # Save message to database
        saved_msg = await self.save_message(
            sender_id=message.sender_id,
            receiver_id=message.receiver_id,
            content=message.content
        )

        # Try to send vis WebSocket if receiver is online
        is_ws_connected = False
        manager = ConnectionManager()
        if message.receiver_id in manager.connected_user_ids:
            try:
                await manager.send_to_user(
                    message.receiver_id,
                    WsMessage(
                        type="message",
                        data=MessageOut.model_validate(saved_msg).dict()
                    )
                )
                is_ws_connected = True
            except Exception:
                # WebSocket failed but we still have the message in DB
                pass

        return MessageResponse(
            success=True,
            message=MessageOut.model_validate(saved_msg),
            is_ws_connected=is_ws_connected
        )

