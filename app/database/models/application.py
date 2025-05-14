"""
SQLAlchemy Application Model
============================

Defines the database schema and ORM mapping for job applications.
This model represents the 'applications' table in the database and 
tracks user applications and their associated ML processing states.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from datetime import datetime
from app.database.base import Base
from app.database.models.enums.application import ApplicationStatus, MLTaskStatus  # <-- Import enums

class Application(Base):
    """
    Job application entity linked to a user and an external job posting.
    
    Attributes:
        id: Primary key identifier
        user_id: Foreign key to the user who submitted the application
        job_id: External identifier for the job
        status: Current state of the application (e.g. pending, completed)
        ml_status: Current state of the ML processing (e.g. queued, success)
        created_at: Timestamp of application creation
        updated_at: Timestamp of last update
        ml_task_id: Optional reference ID for ML task
        error_message: Optional error message from ML processing
    """
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    job_id = Column(String, index=True, nullable=False)  # External job ID
    
    # Using Enums instead of raw strings
    status = Column(Enum(ApplicationStatus), 
                   default=ApplicationStatus.PENDING,
                   nullable=False)
    
    ml_status = Column(Enum(MLTaskStatus),  # <-- Tracks ML pipeline
                      default=MLTaskStatus.QUEUED,
                      nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, 
                       default=datetime.utcnow, 
                       index=True)
    updated_at = Column(DateTime, 
                       default=datetime.utcnow, 
                       onupdate=datetime.utcnow)
    
    # Optional fields
    ml_task_id = Column(String)      # Reference to ML service
    error_message = Column(String)   # Failure details
    
    def __repr__(self):
        return f"<Application(id={self.id}, user_id={self.user_id}, job_id='{self.job_id}')>"