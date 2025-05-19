"""
User Management Service
======================

Handles all business logic related to user account operations:
- User registration
- User data retrieval
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.user import User
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
            HTTPException: 400 if username already exists.
        """
        # Check for existing user
        result = await self.db.execute(select(User).where(User.username == user.username))
        db_user = result.scalar_one_or_none()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
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
        """Update user fields and return updated user object

        Args:
            user_id: ID of the user to update
            update_data: Pydantic model containing fields to update

        Returns:
            Updated User object

        Raises:
            ValueError: If user not found or email already in use
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
        """Update user password and return updated user object
        
        Args:
            user_id: ID of user to update
            new_password: Plain text new password
            
        Returns:
            Updated User object
            
        Raises:
            ValueError: If user not found
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