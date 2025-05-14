from pydantic import BaseModel
from datetime import datetime

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