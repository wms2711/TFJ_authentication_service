"""
Notification Data Schemas
=========================

Defines the data structures for notification handling:
1. API request/response formats
2. Database model representations
3. Internal service transfers

Includes:
- Notification creation (from admins/employers)
- Notification response schema for users
- Internal DB representation for read status
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class NotificationBase(BaseModel):
    """
    Core notification attributes shared across all schemas.

    Used as base for:
    - Notification creation
    - Notification DB representation
    - Output to user

    Fields:
        user_id (int): ID of the user receiving the notification.
        notification_title (str): Title of the notification.
        message (str): Detailed message content.
    """
    user_id: int
    notification_title: str
    message: str

    class Config:
        extra = "forbid"  # Disallow unknown fields

class NotificationCreate(NotificationBase):
    """
    Schema for notification creation requests.

    Used in:
    - POST /notifications endpoint

    Access:
        - Admins
        - Employers

    Fields inherited from NotificationBase:
        user_id, notification_title, message
    """
    pass

    class Config:
        extra = "forbid"  # Disallow unknown fields

class NotificationInDB(NotificationBase):
    """
    Complete notification record with DB metadata.

    Used for:
    - Returning notification to user
    - Internal model validation and serialization

    Fields:
        id (int): Unique identifier of the notification.
        is_read (bool): Whether the user has read this notification.
    """
    id: int
    is_read: bool

    class Config:
        from_attributes = True   # Allow conversion from ORM models