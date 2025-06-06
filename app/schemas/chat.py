"""
Chat Data Schemas
=================

Defines the data structures for chat messaging across layers:
1. WebSocket and HTTP request/response formats
2. Database model representations
3. Internal real-time communication via WebSocket
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.database.models.chat import ChatMessage
from fastapi.encoders import jsonable_encoder

class ChatUser(BaseModel):
    """
    Minimal user representation for chat contact lists.

    Used for:
    - GET /chat/conversations endpoint
    - WebSocket presence status

    Fields:
        id (int): Unique user identifier
        username (str): Display name of the user
        is_online (bool): Real-time presence flag
    """
    id: int
    username: str
    is_online: bool = False

class MessageBase(BaseModel):
    """
    Shared attributes for chat messages.

    Used as base for:
    - Message creation via WebSocket or HTTP

    Fields:
        content (str): The message text body
    """
    content: str

class MessageCreate(MessageBase):
    """
    WebSocket message creation schema.

    Used for:
    - Sending new messages over WebSocket

    Inherits:
        MessageBase

    Fields:
        receiver_id (int): ID of the user receiving the message
    """
    receiver_id: int

class MessageOut(BaseModel):
    """
    Serialized message object for API/WebSocket responses.

    Used for:
    - Returning saved messages via HTTP/WebSocket
    - Message echo or real-time delivery

    Fields:
        id (int): Unique identifier of the message
        sender_id (int): User ID of the sender
        receiver_id (int): User ID of the receiver
        content (str): Text content of the message
        sent_at (datetime): Time when the message was sent
        read_at (Optional[datetime]): Time when the message was read, if any
    """
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
        from_attributes=True  # Enables ORM parsing from SQLAlchemy models
    )

    @classmethod
    def from_db_model(cls, db_message: ChatMessage):
        """
        Convert SQLAlchemy ChatMessage model to MessageOut schema.
        """
        return cls(
            id=db_message.id,
            sender_id=db_message.sender_id,
            receiver_id=db_message.receiver_id,
            content=db_message.content,
            sent_at=db_message.sent_at,
            read_at=db_message.read_at
        )

class WsMessage(BaseModel):
    """
    Envelope format for WebSocket communication.

    Used for:
    - Sending typed messages to clients
    - Distinguishing between chat messages, read receipts, or other event types

    Fields:
        type (str): Event type identifier (e.g. "message", "status", "read_receipt")
        data (dict): Event payload (e.g. serialized MessageOut)
    """
    type: str  # "message", "status", "read_receipt"
    data: dict

    def dict(self, **kwargs):
        """
        Ensure nested structures are serialized for WebSocket transmission.
        """
        return jsonable_encoder(super().model_dump(**kwargs))

class MessageCreateHTTP(MessageCreate):
    """
    HTTP-based message creation schema.

    Used for:
    - POST /chat/messages endpoint

    Inherits:
        MessageCreate

    Fields:
        sender_id (int): ID of the user sending the message
    """
    sender_id: int  # For HTTP where we can't get it from WS connection

class MessageResponse(BaseModel):
    """
    HTTP response for sending a message.

    Used for:
    - POST /chat/messages

    Fields:
        success (bool): Indicates if the message was successfully stored
        message (MessageOut): The stored message content
        is_ws_connected (bool): Whether the recipient was online to receive it via WebSocket
    """
    success: bool
    message: MessageOut
    is_ws_connected: bool