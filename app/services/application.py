"""
Application Management Service
==============================

Handles business logic for job application operations:
- Application creation
- Application status updates
"""

import json
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import Application
from app.database.models.enums.application import ApplicationStatus, MLTaskStatus, SwipeAction, RedisAction
from app.services.redis import RedisService
from app.schemas.application import ApplicationOut, ApplicationUpdate
from fastapi import HTTPException, status
from typing import Optional, Unpack, List
from datetime import datetime
from uuid import UUID, uuid4
from utils.logger import init_logger

# Configure logger
logger = init_logger("ApplicationService")

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

    async def create_application(
            self, 
            user_id: int, 
            job_id: UUID,
            action: SwipeAction
        ) -> ApplicationOut:
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
                action=action,
                status=ApplicationStatus.PENDING,
                ml_status=MLTaskStatus.QUEUED,
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
                
                self.redis.publish_application(app.id, user_id, job_id, RedisAction.APPLY)
            except Exception as redis_exc:
                # Log but don't fail the whole operation if Redis fails
                logger.exception(f"Redis publish failed: {str(redis_exc)}")
                # TODO: Consider whether to continue or raise, based on your requirements

            return ApplicationOut.model_validate(app)
            
        except ValueError as ve:
            await self.db.rollback()
            logger.error(f"Validation error in create_application: {str(ve)}")
            raise  # Re-raise for the router to handle
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error in create_application: {str(e)}", exc_info=True)
            raise ValueError("Failed to create application") from e

    async def record_swipe_history(
        self,
        user_id: int,
        job_id: UUID,
        action: SwipeAction
    ) -> None:
        """
        Keep track of a action for swipe left.

        Flow:
        1. Creates a new `Application` DB record
        2. Commits to database

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
            # Create and save swipe left application
            app = Application(
                user_id=user_id,
                job_id=job_id,
                action=action,
                status=ApplicationStatus.NA,
                ml_status=MLTaskStatus.NA,
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
            return ApplicationOut.model_validate(app)
        
        except ValueError as ve:
            await self.db.rollback()
            logger.error(f"Validation error in create_application: {str(ve)}")
            raise  # Re-raise for the router to handle
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error in create_application: {str(e)}", exc_info=True)
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )
        try:
            stmt = select(Application).where(Application.id == app_id)
            result = await self.db.execute(stmt)
            application = result.scalar_one_or_none()

            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Application not found"
                )
            if application.action != SwipeAction.LIKE:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Application status cannot be updated for this application"
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
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update application: {str(e)}"
            )

    async def get_application_status(
            self, 
            app_id: int
        ) -> ApplicationOut:
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
        try:
            # Validate input
            if not isinstance(app_id, int) or app_id < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid application ID format"
                )
            
            # Get application
            stmt = select(Application).where(Application.id == app_id)
            result = await self.db.execute(stmt)
            application = result.scalar_one_or_none()
            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Application not found"
                )
        
            return ApplicationOut.model_validate(application)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve application: {str(e)}"
            )
    
    async def get_user_applications(
            self,
            requesting_user: int
    ) -> List[ApplicationOut]:
        """
        Retrieve all applications for a specific user.

        Args:
            requesting_user (int): ID of the user whose applications to retrieve.

        Returns:
            List of ApplicationOut objects.

        Raises:
            ValueError: If no applications found (optional).
        """
        try:
            # Generate cache key
            cache_key = f"applications:user:{requesting_user}"

            # Try cache first if Redis is available
            if self.redis:
                try:
                    if cached := await self.redis.get_cache(cache_key):
                        logger.debug(f"Cache hit for applications of user {requesting_user}")
                        return [ApplicationOut.model_validate_json(n) for n in json.loads(cached)]
                except Exception as e:
                    logger.warning(f"Cache check failed, proceeding to DB: {str(e)}")

            # Else query database
            stmt = select(Application).where(
                Application.user_id == requesting_user
            ).order_by(Application.created_at.desc())
            result = await self.db.execute(stmt)
            applications = result.scalars().all()
            logger.info(f"Found {len(applications)} applications")
            serialized_applications = [ApplicationOut.model_validate(application) for application in applications]

            # Update cache
            if self.redis and applications:
                try:
                    await self.redis.set_cache(
                        cache_key,
                        json.dumps([n.model_dump_json() for n in serialized_applications]),
                        ttl=300  # Cache for 5 minutes
                    )
                except Exception as e:
                    logger.error(f"Failed to update applications cache: {str(e)}")

            return serialized_applications
        
        except Exception as e:
            logger.error(f"Failed to retrieve notifications: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve notifications"
            )
        
    async def withdraw_application(
            self,
            app_id: int,
            user_id: int
    ) -> ApplicationOut:
        """
        Withdraw an application by setting status to WITHDRAWN
        
        Args:
            app_id: Application ID to withdraw
            user_id: User ID for verification (already verified in router)
        
        Returns:
            The updated application
        
        Raises:
            ValueError: If application not found or already withdrawn
        """
        try:
            # Get application first and check ownership
            stmt = select(Application).where(Application.id == app_id)
            result = await self.db.execute(stmt)
            application = result.scalar_one_or_none()
            if not application:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Application not found"
                )
            if application.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot withdraw another user's application"
                )
            
            # Check if it is LIKE action
            if application.action != SwipeAction.LIKE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This application is not permitted to redraw (DISLIKE application)"
                )

            # Check if application is already withdrawn
            if application.status == ApplicationStatus.WITHDRAWN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already withdrawn"
                )
            
            # Check if application is failed or rejected
            if application.status in [ApplicationStatus.FAILED, ApplicationStatus.REJECTED]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot withdraw this application, this application is already processed"
                )

            # Withdraw
            application.status = ApplicationStatus.WITHDRAWN
            application.updated_at = datetime.utcnow()
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                raise ValueError(f"Database commit failed: {str(db_exc)}")
                
            await self.db.refresh(application)

            if not application.id:
                raise ValueError("Failed to retrieve application ID after insert")

            # Publish to Redis
            try:
                if self.redis is None:
                    raise RuntimeError("Redis service not configured")
                
                self.redis.publish_application(application.id, user_id, application.job_id, RedisAction.WITHDRAW)
            except Exception as redis_exc:
                # Log but don't fail the whole operation if Redis fails
                logger.exception(f"Redis publish failed: {str(redis_exc)}")
                # TODO: Consider whether to continue or raise, based on your requirements
            return ApplicationOut.model_validate(application)

        except HTTPException:
            raise
        except ValueError as ve:
            await self.db.rollback()
            logger.error(f"Validation error in withdraw_application: {str(ve)}")
            raise  # Re-raise for the router to handle
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error in withdraw_application: {str(e)}", exc_info=True)
            raise ValueError("Failed to withdraw application") from e