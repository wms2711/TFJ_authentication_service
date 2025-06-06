from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, func
from fastapi import WebSocket, HTTPException, status, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from typing import Dict, List

from app.database.models.user import User
from app.database.models.chat import ChatMessage
from app.schemas.chat import ChatUser, MessageOut, MessageCreateHTTP, MessageResponse, WsMessage

class ConnectionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_connections = {}
        return cls._instance
    
    def __init__(self):
        pass

    @property
    def connected_user_ids(self) -> List[int]:
        return list(self.active_connections.keys())

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print("ADDED", self.active_connections)

    def disconnect(self, user_id: int, websocket: WebSocket = None):
        if websocket:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:  # No remaining connections
                del self.active_connections[user_id]
        else:
            self.active_connections.pop(user_id, None)
        print("DELETE CONNECTION", user_id, "NEW conntion list is", self.active_connections)

    async def send_to_user(self, user_id: int, message: WsMessage):
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
    def __init__(self, db: AsyncSession):
        self.db = db
        self.manager = ConnectionManager()

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
                is_online=user.id in self.manager.connected_user_ids
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
            except Exception:
                # WebSocket failed but we still have the message in DB
                pass


        return MessageResponse(
            success=True,
            message=MessageOut.model_validate(saved_msg),
            is_ws_connected=is_ws_connected
        )
    
    async def handle_websocket_connection(self, websocket: WebSocket, user_id: int):
        """Handle the entire WebSocket connection lifecycle"""
        await self.manager.connect(websocket, user_id)
        
        try:
            while True:
                await self._handle_websocket_message(websocket, user_id)
        except WebSocketDisconnect:
            self.manager.disconnect(user_id)
        except Exception as e:
            print(f"WebSocket error: {e}")
            self.manager.disconnect(user_id)

    async def _handle_websocket_message(self, websocket: WebSocket, user_id: int):
        """Process an incoming WebSocket message"""
        data = await websocket.receive_json()
        message = WsMessage(**data)
        
        if message.type == "message":
            await self._handle_chat_message(user_id, message.data)
        elif message.type == "read_receipt":
            await self._handle_read_receipt(user_id, message.data)

    async def _handle_chat_message(self, sender_id: int, message_data: dict):
        """Process a chat message received via WebSocket"""

        if sender_id == message_data["receiver_id"]:
            print(f"Ignored self-chat attempt by user {sender_id}")
            return
        
        # Save message to database
        saved_msg = await self.save_message(
            sender_id=sender_id,
            receiver_id=message_data["receiver_id"],
            content=message_data["content"]
        )
            
        # Create MessageOut instance directly from SQLAlchemy model
        message_out = MessageOut.from_db_model(saved_msg)
        
        # Create the WebSocket message
        ws_message = WsMessage(
            type="message",
            data=jsonable_encoder(message_out.model_dump())
        )
        
        # Send confirmation to sender (Message echo)
        await self.manager.send_to_user(sender_id, ws_message)
        
        print("BEFORE", message_data["receiver_id"], self.manager.connected_user_ids)
        # Send to receiver if online
        if message_data["receiver_id"] in self.manager.connected_user_ids:
            await self.manager.send_to_user(
                message_data["receiver_id"],
                ws_message
            )

    async def _handle_read_receipt(self, receiver_id: int, receipt_data: dict):
        """Process a read receipt received via WebSocket"""
        await self.mark_messages_as_read(
            sender_id=receipt_data["sender_id"],
            receiver_id=receiver_id
        )

