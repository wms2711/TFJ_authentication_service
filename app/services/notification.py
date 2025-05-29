"""
Notification Service
====================

Handles business logic for sending and managing user notifications:
- Admins and Employers can send notifications to users.
- Users can view their own notifications.
- Users can mark notifications as read.

Security:
---------
- Only admins and employers can create/send notifications.
- Only the owner of a notification can mark it as read.
"""

import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime
from app.database.models.user import User
from app.database.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationInDB
from app.services.redis import RedisService
from utils.logger import init_logger

# Configure logger
logger = init_logger("NotificationService")

class NotificationService:
    """Service for notification management"""

    def __init__(
            self,
            db: AsyncSession,
            redis_service: Optional[RedisService] = None
        ):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db
        self.redis = redis_service

    async def create_notification(
            self, 
            notification_payload: NotificationCreate, 
            requesting_user: User
        ) -> NotificationInDB:
        """
        Create a new notification for a specific user.
        Restricted to admins and employers.

        Flow:
        1. Validates if requesting user is admin or employer.
        2. Ensures target user exists and is active.
        3. Creates and stores notification in database.

        Args:
            notification_payload (NotificationCreate): Payload with target user and message details.
            requesting_user (User): Authenticated user making the request.

        Returns:
            NotificationInDB: Newly created notification.

        Raises:
            HTTPException:
                - 403 if the user lacks permission.
                - 404 if target user does not exist.
                - 500 if notification creation fails.
        """
        if not requesting_user.is_admin and not requesting_user.is_employer:
            logger.error(f"Non-admin or non-employer user of user id: {requesting_user.id} attempted to create notification")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges / Employer status required"
            )
        try:
            # Find user exist and active
            stmt = select(User).where(User.id == notification_payload.user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                logger.warning(f"User not found with user_id: {notification_payload.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with username '{notification_payload.user_id}' not found"
                )
            if not user.is_active:
                logger.warning(f"User is inactive with user_id: {notification_payload.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User with username '{notification_payload.user_id}' is inactive"
                )
            
            # Create notification
            notification = Notification(
                user_id=notification_payload.user_id,
                notification_title=notification_payload.notification_title,
                message=notification_payload.message,
                created_at=datetime.utcnow()
            )
            self.db.add(notification)
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(notification)
            return notification
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create notification for {notification_payload.user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notification"
            )
        
    async def get_notifications_for_user(
            self, 
            requesting_user: User
        ) -> List[NotificationInDB]:
        """
        Retrieve all notifications for the authenticated user.

        Flow:
        1. Uses user ID from request to filter notifications.
        2. Returns serialized list of notifications.

        Args:
            requesting_user (User): Authenticated user making the request.

        Returns:
            List[NotificationInDB]: List of notifications belonging to the user.

        Raises:
            HTTPException:
                - 500 if retrieval fails.
        """
        try:
            # Generate cache key
            cache_key = f"notifications:user:{requesting_user.id}"

            # Try cache first if Redis is available
            if self.redis:
                try:
                    if cached := await self.redis.get_cache(cache_key):
                        logger.debug(f"Cache hit for notifications of user {requesting_user.id}")
                        return [NotificationInDB.model_validate_json(n) for n in json.loads(cached)]
                except Exception as e:
                    logger.warning(f"Cache check failed, proceeding to DB: {str(e)}")

            # Else query database
            result = await self.db.execute(
                select(Notification).where(Notification.user_id == requesting_user.id)
            )
            notifications = result.scalars().all()
            logger.info(f"Found {len(notifications)} notifications")
            serialized_notifications = [NotificationInDB.model_validate(notification) for notification in notifications]

            # Update cache
            if self.redis and notifications:
                try:
                    await self.redis.set_cache(
                        cache_key,
                        json.dumps([n.model_dump_json() for n in serialized_notifications]),
                        ttl=300  # Cache for 5 minutes
                    )
                except Exception as e:
                    logger.error(f"Failed to update notifications cache: {str(e)}")

            return serialized_notifications
        
        except Exception as e:
            logger.error(f"Failed to retrieve notifications: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve notifications"
            )
        
    async def mark_as_read(
            self,
            notif_id: int, 
            requesting_user: User
        ) -> NotificationInDB:
        """
        Mark a specific notification as read.
        Only the notification owner can perform this action.

        Flow:
        1. Validates notification exists.
        2. Checks if current user is the owner.
        3. Marks as read and updates `updated_at`.

        Args:
            notif_id (int): ID of the notification to mark as read.
            requesting_user (User): Authenticated user making the request.

        Returns:
            NotificationInDB: Updated notification object.

        Raises:
            HTTPException:
                - 404 if notification not found.
                - 403 if user is not the owner.
                - 500 if update fails.
        """
        try:
            stmt = select(Notification).where(Notification.id == notif_id)
            result = await self.db.execute(stmt)
            notif = result.scalar_one_or_none()
            if not notif:
                logger.warning(f"Notification not found with notif_id: {notif_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Notification does not exist"
                )
            if requesting_user.id != notif.user_id:
                logger.warning(f"This user_id {requesting_user.id} has no permission adjusting notification from user_id {notif.user_id}, notif_id {notif_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have permission to update"
                )
            
            notif.is_read = True
            notif.updated_at = datetime.utcnow()
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed for notif_id={notif_id}: {db_exc}")
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(notif)
            return notif
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error during notification update for notif_id={notif_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update notifications"
            )