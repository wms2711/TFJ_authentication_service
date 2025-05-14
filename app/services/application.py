from sqlalchemy.orm import Session
from app.database.models.application import Application
from app.services.redis import RedisService
from app.schemas.application import ApplicationOut
from fastapi import HTTPException
from typing import Optional
from datetime import datetime

class ApplicationService:
    def __init__(self, db: Session, redis: Optional[RedisService] = None):
        self.db = db
        self.redis = redis

    def create_application(self, user_id: int, job_id: str) -> ApplicationOut:
        app = Application(
            user_id=user_id,
            job_id=job_id,
            status="pending"
        )
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        
        # Publish to Redis
        if self.redis is None:
            raise RuntimeError(f"Redis service is not available. Cannot publish.")
        
        self.redis.publish_application(app.id)
        
        return ApplicationOut.model_validate(app)
    
    def update_application_status(self, app_id: int, status: Optional[str] = None, ml_status: Optional[str] = None) -> ApplicationOut:
        app = self.db.query(Application).filter(Application.id == app_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        if status:
            app.status = status
        if ml_status:
            app.ml_status = ml_status
        if not status and not ml_status:
            raise HTTPException(status_code=400, detail="No fields to update")
        app.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(app)
        
        return ApplicationOut.model_validate(app)