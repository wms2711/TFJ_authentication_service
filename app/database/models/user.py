"""
SQLAlchemy User Model
====================

Defines the database schema and ORM mapping for user accounts.
This model represents the 'user' table in the database.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

class User(Base):
    """
    User account entity representing an authenticated system user.
    
    Attributes:
        id: Primary key identifier
        username: Unique login identifier
        email: Unique contact email
        hashed_password: Securely stored password hash
        is_active: Account status flag
        full_name: Optional display name
        email_verified: Email verification status
        is_employer: Flag for employer accounts
        is_admin: Flag for admin accounts
    """

    # Database table name
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    full_name = Column(String(100), nullable=True)

    # Verify
    email_verified = Column(Boolean, default=False)

    # Employer
    is_employer = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Relationship to profile (one-to-one)
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Relationship to notification (one-to-one)
    profile = relationship("Notification", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Relationship to application (Keep application table independent from user table)
        # Reason: For tracking of applications even after user has self-delete profile
    # application = relationship("Application", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        """
        Official string representation of User instance.
        
        Returns:
            str: Descriptive representation
        """
        return f"<User(id={self.id}, username={self.username}, roles=[employer:{self.is_employer}, admin:{self.is_admin}]>"