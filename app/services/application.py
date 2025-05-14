"""
Application Management Service
==============================

Handles business logic for job application operations:
- Application creation
- Application status updates
"""

from sqlalchemy.orm import Session
from app.database.models.application import Application
from app.services.redis import RedisService
from app.schemas.application import ApplicationOut
from fastapi import HTTPException
from typing import Optional
from datetime import datetime

class ApplicationService:
    """Main application service handling job applications."""

    def __init__(self, db: Session, redis: Optional[RedisService] = None):
        """
        Initialize service with database session and optional Redis client.

        Args:
            db (Session): SQLAlchemy database session
            redis (Optional[RedisService]): Redis pub-sub handler for event messaging
        """
        self.db = db
        self.redis = redis

    def create_application(self, user_id: int, job_id: str) -> ApplicationOut:
        """
        Submit a new job application.

        Flow:
        1. Creates a new `Application` DB record
        2. Commits to database
        3. Publishes application ID to Redis

        Args:
            user_id (int): ID of the user submitting the application
            job_id (str): External job identifier (from job board or catalog)

        Returns:
            ApplicationOut: Serialized application details for response

        Raises:
            RuntimeError: If Redis is required but not configured
        """
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
        
        self.redis.publish_application(app.id, user_id, job_id)
        
        return ApplicationOut.model_validate(app)
    
    def update_application_status(self, app_id: int, status: Optional[str] = None, ml_status: Optional[str] = None) -> ApplicationOut:
        """
        Update the status of an existing application.

        Flow:
        1. Fetches application by ID
        2. Updates `status`, `ml_status`, or both
        3. Commits changes to database

        Args:
            app_id (int): ID of the application to update
            status (Optional[str]): New lifecycle status (e.g., "completed", "failed")
            ml_status (Optional[str]): New ML processing status (e.g., "running", "success")

        Returns:
            ApplicationOut: Updated application details

        Raises:
            HTTPException: 404 if application not found
            HTTPException: 400 if no fields provided for update
        """
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
    
    def get_application_status(self, app_id: int) -> ApplicationOut:
        """
        Get existing application.

        Flow:
        1. Fetches application by ID

        Args:
            app_id (int): ID of the application to update

        Returns:
            ApplicationOut: Updated application details

        Raises:
            HTTPException: 404 if application not found
        """
        app = self.db.query(Application).filter(Application.id == app_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return ApplicationOut.model_validate(app)