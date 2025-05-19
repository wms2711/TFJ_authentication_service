"""
User Management Service
======================

Handles all business logic related to user account operations:
- User registration
- User data retrieval
"""

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
from app.database.models.profile import UserProfile
from app.schemas.user import UserCreate, UserInDB, UserUpdate, UserPasswordUpdate
from app.services.auth import AuthService

class UserService:
    """Main user service handling account management."""

    def __init__(self, db: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db

    async def create_user(self, user: UserCreate) -> User:
        """
        Register a new user account.
        
        Flow:
        1. Checks username availability.
        2. Hashes password.
        3. Creates user record.
        4. Commits to database.
        
        Args:
            user (UserCreate): For registration of user data.
            
        Returns:
            User: Created SQLAlchemy user model.
            
        Raises:
            HTTPException: 400 if username or email already exists.
        """
        # Check for existing username
        username_result = await self.db.execute(
            select(User).where(User.username == user.username))
        if username_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check for existing email
        email_result = await self.db.execute(
            select(User).where(User.email == user.email))
        if email_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password before storage
        hashed_password = AuthService(self.db).get_password_hash(user.password)
        
        # Create new user record
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name
        )

        # Persist to database
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user
    
    async def update_user(self, user_id: int, update_data: dict) -> None:
        """Update user fields and return updated user object.

        Args:
            user_id: ID of the user to update.
            update_data: Pydantic model containing fields to update.

        Returns:
            Updated User object.

        Raises:
            ValueError: If user not found or email already in use.
        """
        # Retrieve the user from the database
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise ValueError("User not found")
        
        # Extract only provided fields to update
        data_to_update = update_data.dict(exclude_unset=True)

        # Validate email uniqueness if being changed
        if "email" in data_to_update and data_to_update["email"] != user.email:
            existing_user = await AuthService(self.db).get_user_by_email(data_to_update["email"])
            if existing_user:
                raise ValueError("Email already in use")
            
        # Update user information
        for field, value in data_to_update.items():
            setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user

    async def update_password(self, user_id: int, new_password: UserPasswordUpdate) -> User:
        """Update user password and return updated user object.
        
        Args:
            user_id: ID of user to update.
            new_password: Plain text new password.
            
        Returns:
            Updated User object.
            
        Raises:
            ValueError: If user not found.
        """
        # Get user from database
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if not user:
            raise ValueError("User not found")
        
        # Hash the new password
        hashed_password = AuthService(self.db).get_password_hash(new_password)
        
        # Update and commit
        user.hashed_password = hashed_password
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def delete_user(self, user_id: int) -> None:
        """
        Permanently delete a user account and related profile.
        
        Flow:
        1. Verify user exists.
        2. Delete associated profile (if exists).
        3. Delete user record.
        4. Commit transaction.
        
        Args:
            user_id: ID of the user to delete.
            
        Raises:
            ValueError: If user not found.
            HTTPException: If deletion fails (converted in router layer).
        """
        try:
            # 1. Get the user with profile eagerly loaded
            result = await self.db.execute(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.profile))
            )
            user = result.scalars().first()

            if not user:
                raise ValueError("User not found")

            # 2. Delete associated profile if exists
            if user.profile:
                await self.db.delete(user.profile)
                await self.db.flush()
            
            # 3. Delete the user record
            await self.db.delete(user)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            raise ValueError(f"Failed to delete user: {str(e)}") from e

    async def mark_email_as_verified(self, email: str) -> None:
        """
        Mark a user's email as verified in the database.
        
        Args:
            email: Email address to verify
        """
        result = await self.db.execute(
            update(User)
            .where(User.email == email)
            .values(email_verified=True)
        )
        await self.db.commit()

    # def get_user_by_username(self, username: str) -> User | None:
    #     """
    #     Retrieve user by unique username.
        
    #     Args:
    #         username: Exact username to search
            
    #     Returns:
    #         User: If user found
    #         None: If user doesn't exist
    #     """
    #     return self.db.query(User).filter(User.username == username).first()