"""
Notification Data Schemas
=========================

Defines the data structures for notification handling:
1. API request/response formats
2. Database model representations
3. Internal service transfers

Includes:
- Notifications creation
- notifications output schema
- Notification patching (mark as read)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class NotificationBase(BaseModel):
    user_id: int
    notification_title: str
    message: str

    class Config:
        extra = "forbid"  # Disallow unknown fields

class NotificationCreate(NotificationBase):
    """
    Schema for notification creation requests from admins and employers

    Fields:
        user_id (int): User id that admin or eployer wants to message to.
        notification_title (str): title.
        message (str): message of the notification.
    """
    pass

    class Config:
        extra = "forbid"  # Disallow unknown fields

class NotificationInDB(NotificationBase):
    id: int
    is_read: bool

    class Config:
        from_attributes = True