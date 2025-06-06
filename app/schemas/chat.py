from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.database.models.chat import ChatMessage
from fastapi.encoders import jsonable_encoder

class ChatUser(BaseModel):
    id: int
    username: str
    is_online: bool = False

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    receiver_id: int

class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    sent_at: datetime
    read_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        },
        from_attributes=True  # This enables ORM mode
    )

    @classmethod
    def from_db_model(cls, db_message: ChatMessage):
        return cls(
            id=db_message.id,
            sender_id=db_message.sender_id,
            receiver_id=db_message.receiver_id,
            content=db_message.content,
            sent_at=db_message.sent_at,
            read_at=db_message.read_at
        )

class WsMessage(BaseModel):
    type: str  # "message", "status", "read_receipt"
    data: dict  # This will contain the serialized MessageOut

    def dict(self, **kwargs):
        """Ensure proper serialization"""
        return jsonable_encoder(super().model_dump(**kwargs))

class MessageCreateHTTP(MessageCreate):
    sender_id: int  # For HTTP where we can't get it from WS connection

class MessageResponse(BaseModel):
    success: bool
    message: MessageOut
    is_ws_connected: bool