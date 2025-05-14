from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from datetime import datetime
from app.database.base import Base
from app.database.models.enums.application import ApplicationStatus, MLTaskStatus  # <-- Import enums

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
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