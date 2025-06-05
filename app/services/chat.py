from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, func
from fastapi import WebSocket
from datetime import datetime
from typing import Dict, List

from app.database.models.user import User
from app.database.models.chat import ChatMessage
from app.schemas.chat import ChatUser, MessageOut

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

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
                is_online=user.id in ConnectionManager().active_connections
            )
            for user in users
        ]
    
    async def get_user_messages(
            self,
            user1_id: int,
            user2_id: int
        ) -> List[MessageOut]:
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

        return [MessageOut.model_validate(msg) for msg in messages]