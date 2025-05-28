from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List
import logging
from app.database.models.user import User
from app.schemas.user import UserInDB, UserUpdateAdmin
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AdminService:
    """Service for admin-specific operations"""

    def __init__(self, db: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db

    async def get_all_users(self, requesting_user: User) -> List[UserInDB]:
        """
        Retrieve all users (admin only).
        
        Args:
            requesting_user: User making the request (must be admin).
            
        Returns:
            List of all users.
            
        Raises:
            HTTPException: 403 if user is not admin.
        """
        if not requesting_user.is_admin:
            logger.error(f"Non-admin user {requesting_user.id} attempted to list all users")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
            
        try:
            result = await self.db.execute(select(User))
            users = result.scalars().all()
            logger.info(f"Found {len(users)} users")
            return [UserInDB.model_validate(user) for user in users]
        
        except Exception as e:
            logger.error(f"Failed to retrieve users: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve users"
            )
        
    async def update_user(
            self, 
            user_id: int, 
            update_data: UserUpdateAdmin,
            requesting_user: User
        ) -> UserInDB:
        """
        Admin-only user updates.
        
        Args:
            user_id (int): ID of user to update.
            update_data (UserUpdateAdmin): Fields to modify.
            requesting_user (User): Admin making the change.
            
        Returns:
            Updated user data.
            
        Raises:
            HTTPException: 403 if not admin, 404 if user not found.
        """
        if not requesting_user.is_admin:
            logger.error(f"Non-admin user {requesting_user.id} attempted to list all users")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        try:
            # Get target user
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()
            
            if not user:
                logger.error(f"User {user_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Prevent self-modification of admin status
            if user.id == requesting_user.id:
                logger.error(f"Admin {requesting_user.id} attempted self-demotion")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins are not allowed to modify your own status, contact developers"
                )
            
            # Apply updates
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(user, field, value)

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(user)

            return UserInDB.model_validate(user)
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )