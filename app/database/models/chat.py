"""
SQLAlchemy Chat Message Model
====================

Defines the database schema and ORM mapping for user accounts.
This model represents the 'chat_messages' table in the database.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.base import Base

class ChatMessage(Base):
    """
    Chat message entity representing a direct message between two users.

    Attributes:
        id: Primary key identifier for the message
        sender_id: Foreign key referencing the sender user ID
        receiver_id: Foreign key referencing the receiver user ID
        content: Text content of the message
        sent_at: Timestamp of when the message was sent
        read_at: Timestamp of when the message was read (nullable)
        sender: ORM relationship to the sender User
        receiver: ORM relationship to the receiver User
    """

    # Database table name
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    content = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    def __repr__(self):
        """
        Official string representation of ChatMessage instance.

        Returns:
            str: Descriptive representation
        """
        return f"<ChatMessage(id={self.id}, sender_id={self.sender_id}, receiver_id={self.receiver_id}, sent_at={self.sent_at})>"
