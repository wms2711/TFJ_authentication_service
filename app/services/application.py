"""
Application Management Service
==============================

Handles business logic for job application operations:
- Application creation
- Application status updates
"""

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import Application
from app.services.redis import RedisService
from app.schemas.application import ApplicationOut, ApplicationUpdate
from fastapi import HTTPException
from typing import Optional, Unpack
from datetime import datetime

class ApplicationService:
    """Main application service handling job applications."""

    def __init__(self, db: AsyncSession, redis: Optional[RedisService] = None):
        """
        Initialize service with database session and optional Redis client.

        Args:
            db (AsyncSession): SQLAlchemy async database session.
            redis (Optional[RedisService]): Redis pub-sub handler for event messaging.
        """
        self.db = db
        self.redis = redis

    async def create_application(self, user_id: int, job_id: str) -> ApplicationOut:
        """
        Submit a new job application.

        Flow:
        1. Creates a new `Application` DB record
        2. Commits to database
        3. Publishes application ID to Redis
        4. Returns the created application

        Args:
            user_id: ID of the user submitting the application
            job_id: External job identifier (from job board or catalog)

        Returns:
            ApplicationOut: Serialized application details

        Raises:
            ValueError: For invalid inputs or database operations
            RuntimeError: If Redis is required but not configured
            HTTPException: Should be raised by the router for HTTP status codes
        """
        try:
            # # Validate inputs (example - adjust based on your requirements)
            # if not user_id or user_id < 1:
            #     raise ValueError("Invalid user ID")
            # if not job_id or not isinstance(job_id, str):
            #     raise ValueError("Invalid job ID")

            # Create and save application
            app = Application(
                user_id=user_id,
                job_id=job_id,
                status="pending"
            )
            
            self.db.add(app)
            
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                raise ValueError(f"Database commit failed: {str(db_exc)}")
                
            await self.db.refresh(app)

            if not app.id:
                raise ValueError("Failed to retrieve application ID after insert")

            # Publish to Redis
            try:
                if self.redis is None:
                    raise RuntimeError("Redis service not configured")
                
                self.redis.publish_application(app.id, user_id, job_id)
            except Exception as redis_exc:
                # Log but don't fail the whole operation if Redis fails
                print(f"Redis publish failed: {str(redis_exc)}")
                # TODO: Consider whether to continue or raise, based on your requirements

            return ApplicationOut.model_validate(app)
            
        except ValueError as ve:
            await self.db.rollback()
            print(f"Validation error in create_application: {str(ve)}")
            raise  # Re-raise for the router to handle
        except Exception as e:
            await self.db.rollback()
            print(f"Unexpected error in create_application: {str(e)}", exc_info=True)
            raise ValueError("Failed to create application") from e
    
    async def update_application_status(
            self, 
            app_id: int, 
            **kwargs: Unpack[ApplicationUpdate]
        ) -> ApplicationOut:
        """
        Update the status of an existing application.

        Flow:
        1. Fetches application by ID.
        2. Updates `status`, `ml_status`, or both.
        3. Commits changes to database.

        Args:
            app_id (int): ID of the application to update.
            status (Optional[str]): New lifecycle status (e.g., "completed", "failed").
            ml_status (Optional[str]): New ML processing status (e.g., "running", "success").

        Returns:
            ApplicationOut: Updated application details.

        Raises:
            HTTPException: 404 if application not found.
            HTTPException: 400 if no fields provided for update.
        """
        # Validate inputs
        if not kwargs:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )
        try:
            stmt = select(Application).where(Application.id == app_id)
            result = await self.db.execute(stmt)
            application = result.scalar_one_or_none()

            if not application:
                raise HTTPException(
                    status_code=404, 
                    detail="Application not found"
                )
            # Apply updates
            for field, value in kwargs.items():
                setattr(application, field, value)
            application.updated_at = datetime.utcnow()

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(application)
    
            return ApplicationOut.model_validate(application)
        
        except HTTPException:
            raise
        except Exception as e:
        # Automatic rollback occurs on exception
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update application: {str(e)}"
            )

    
    async def get_application_status(self, app_id: int) -> ApplicationOut:
        """
        Get existing application.

        Flow:
        1. Fetches application by ID.

        Args:
            app_id (int): ID of the application to update.

        Returns:
            ApplicationOut: Updated application details.

        Raises:
            HTTPException: 404 if application not found.
        """
        stmt = select(Application).where(Application.id == app_id)
        result = await self.db.execute(stmt)
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return ApplicationOut.model_validate(app)