"""
Application Data Schemas
========================

Defines the data structures for job application management across layers:
1. API request/response formats
2. Database model representations
3. Internal service communication
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.database.models.enums.application import ApplicationStatus, MLTaskStatus, SwipeAction
from uuid import UUID

class ApplicationBase(BaseModel):
    """
    Shared attributes across application-related schemas.

    Used as base for:
    - Application creation
    - Output serialization

    Fields:
        job_id (UUID): External job identifier
    """
    job_id: UUID
    
class ApplicationCreate(ApplicationBase):
    """
    Application creation schema.

    Used for:
    - POST /application endpoint to submit new applications

    Inherits:
        ApplicationBase
    
    Fields:
        swipe_action (SwipeAction): swipe left or right 
    """
    swipe_action: SwipeAction
    class Config:
        extra = "forbid"  # Disallow unknown fields


class ApplicationOut(ApplicationBase):
    """
    Complete application representation.

    Used for:
    - API responses to return full application details

    Fields:
        id (int): Application ID
        user_id (int): ID of the user who submitted the application
        status (str): Application lifecycle status
        created_at (datetime): Timestamp of application creation
        updated_at (datetime): Timestamp of last modification
        action (SwipeAction): like or dislike 
    """
    id: int
    user_id: int
    status: str
    ml_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    action: SwipeAction
    
    class Config:
        from_attributes = True

class ApplicationUpdate(BaseModel):
    """
    Partial update schema for application status tracking.

    Used for:
    - PATCH /application/{id} endpoint to update status fields

    Fields:
        status (Optional[ApplicationStatus]): New application status
        ml_status (Optional[MLTaskStatus]): New ML pipeline status
    """
    status: Optional[ApplicationStatus] = None
    ml_status: Optional[MLTaskStatus] = None
    class Config:
        extra = "forbid"  # Prevent unexpected fields