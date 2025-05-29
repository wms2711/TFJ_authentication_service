from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List
from datetime import datetime
from app.database.models.user import User
from app.database.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationInDB
from utils.logger import init_logger

# Configure logger
logger = init_logger("NotificationService")

class NotificationService:
    """Service for notification management"""

    def __init__(self, db: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db

    async def create_notification(
            self, 
            notification_payload: NotificationCreate, 
            requesting_user: User
        ) -> NotificationInDB:

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