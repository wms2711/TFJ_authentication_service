from sqlalchemy.orm import Session
from app.database.models.application import Application
from app.services.redis import RedisService
from app.schemas.application import ApplicationOut

class ApplicationService:
    def __init__(self, db: Session, redis: RedisService):
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
        self.redis.publish_application(app.id)
        return ApplicationOut.model_validate(app)