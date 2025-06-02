"""
SQLAlchemy User Profile Model
============================

Defines the database schema and ORM mapping for user profiles.
This model represents the 'user_profiles' table in the database.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList
from app.database.base import Base

class UserProfile(Base):
    """
    Extended user profile information entity.
    
    Attributes:
        id: Primary key identifier
        user_id: Foreign key to associated user account
        (various profile fields as shown below)
    """

    # Database table name
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, nullable=False)
    
    # Personal Information (Full name in user table)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    phone_number = Column(String(20), nullable=True)
    address = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # Professional Information
    headline = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)
    current_position = Column(String(100), nullable=True)
    current_company = Column(String(100), nullable=True)
    years_of_experience = Column(Integer, nullable=True)
    
    # Education
    education = Column(JSON, nullable=True)  # List of degrees/institutions
    
    # Work Experience
    experience = Column(JSON, nullable=True)  # List of jobs/positions
    
    # Skills
    skills = Column(JSON, nullable=True)  # List of skills with proficiency
    
    # Resume/CV
    resumes = Column(MutableList.as_mutable(JSON), default=list)  # Stores array of resume object, tracks in place mutations on hte resumes list
    current_resume_id = Column(String, nullable=True)  # ID of currently active resume
    
    # Job Preferences
    preferred_job_titles = Column(JSON, nullable=True)
    preferred_locations = Column(JSON, nullable=True)
    preferred_salary = Column(String(50), nullable=True)
    job_type_preferences = Column(JSON, nullable=True)  # full-time, part-time, etc.
    
    # Visibility Settings
    is_profile_public = Column(Boolean, default=True)
    is_resume_public = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship back to User
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        """
        Official string representation of UserProfile instance.
        
        Returns:
            str: Descriptive representation
        """
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"