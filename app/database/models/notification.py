"""
SQLAlchemy Notification Model
============================

Defines the database schema and ORM mapping for notification handling.
This model represents the 'notifications' table in the database.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from app.database.base import Base

class Notification(Base):
    """
    Extended notifications entity.
    
    Attributes:
        id: Primary key identifier.
        user_id: Foreign key to associated user account.
        notification_title: Title.
        message: Notification message.
        is_read: If notification is read.
        created_at: Notification creation.
        updated_at: Updating of notification.
    """

    # Database table name
    __tablename__ = "notifications"

    # Notification creation
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # User read messages
    is_read = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        """
        Official string representation of Notification instance.
        
        Returns:
            str: Descriptive representation
        """
        return f"<Notification(id={self.id}, user_id={self.user_id})>"