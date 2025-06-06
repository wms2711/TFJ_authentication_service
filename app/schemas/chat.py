from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ChatUser(BaseModel):
    id: int
    username: str
    is_online: bool = False

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    receiver_id: int

class MessageOut(MessageBase):
    id: int
    sender_id: int
    receiver_id: int
    sent_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class WsMessage(BaseModel):
    type: str  # "message", "status", "read_receipt"
    data: dict

class MessageCreateHTTP(MessageCreate):
    sender_id: int  # For HTTP where we can't get it from WS connection

class MessageResponse(BaseModel):
    success: bool
    message: MessageOut
    is_ws_connected: bool