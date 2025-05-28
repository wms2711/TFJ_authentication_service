"""
Admin Management Service
========================

Handles business logic for admin-only user operations:
- View all registered users (admin only)
- Update user roles and statuses (admin, not allowed to update other admins or own status)
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List
from app.database.models.user import User
from app.schemas.user import UserInDB, UserUpdateAdmin
from utils.logger import init_logger

# Configure logger
logger = init_logger("AdminService")

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
        Retrieve all users in the system. Restricted to admin users.

        Flow:
        1. Verifies the requesting user has admin rights.
        2. Queries all users from the database.
        3. Returns list of serialized user data.

        Args:
            requesting_user (User): User making the request. Must be an admin.

        Returns:
            List[UserInDB]: Serialized list of users.

        Raises:
            HTTPException: 
                - 403 if the requesting user is not an admin.
                - 500 if retrieval fails.
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
        Update another user's details. Restricted to admin users.

        Flow:
        1. Validates requesting user is an admin.
        2. Fetches target user by ID.
        3. Applies update fields from `UserUpdateAdmin`.
        4. Blocks:
           - Updating other admins.
           - Admins demoting themselves.
        5. Commits update and returns updated user.

        Args:
            user_id (int): ID of the user to update.
            update_data (UserUpdateAdmin): Fields to modify.
            requesting_user (User): Admin performing the update.

        Returns:
            UserInDB: Updated user data.

        Raises:
            HTTPException:
                - 403 if the user is not an admin or tries to demote themselves.
                - 404 if the target user does not exist.
                - 500 if update fails.
        """
        if not requesting_user.is_admin:
            logger.error(f"Non-admin user of user id: {requesting_user.id} attempted to list all users")
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
            if user.is_admin:
                logger.error(f"Not allowed to update status of other admins")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not allowed to update status of other admins"
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