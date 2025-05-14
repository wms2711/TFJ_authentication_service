from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.database.models.enums.application import ApplicationStatus, MLTaskStatus

class ApplicationBase(BaseModel):
    job_id: str
    
class ApplicationCreate(ApplicationBase):
    pass

class ApplicationOut(ApplicationBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus]
    ml_status: Optional[MLTaskStatus]