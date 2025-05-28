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
from utils.logger import init_logger

# Configure logger
logger = init_logger("UserService")

class UserService:
    """Main user service handling account management."""

    def __init__(self, db: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db

    async def create_user(
            self, 
            user: UserCreate
        ) -> User:
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
        try:
            # Check for existing username
            username_result = await self.db.execute(
                select(User).where(User.username == user.username)
            )
            if username_result.scalar_one_or_none():
                logger.error(f"Username already registered")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
        
            # Check for existing email
            email_result = await self.db.execute(
                select(User).where(User.email == user.email)
            )
            if email_result.scalar_one_or_none():
                logger.error(f"Email already registered")
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

            self.db.add(db_user)

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed for {user.email}: {db_exc}")
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            
            await self.db.refresh(db_user)
            return db_user
        
        except HTTPException:
            raise
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error during user creation for {user.email}: {e}")
            raise ValueError("Unexpected error during user creation")
    
    async def update_user(
            self, 
            user_id: int, 
            update_data: UserUpdate
        ) -> User:
        """
        Update user fields and return updated user object.

        Args:
            user_id (int): ID of the user to update.
            update_data (UserUpdate): Pydantic model containing fields to update.

        Returns:
            User: Updated user.

        Raises:
            HTTPException: 404 if user not found.
            HTTPException: 400 if email already in use.
            ValueError: On unexpected internal errors.
        """
        try:
            # Retrieve the user from the database
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()
            if not user:
                logger.error(f"User not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Extract only provided fields to update
            data_to_update = update_data.dict(exclude_unset=True)

            # Validate email uniqueness if being changed
            if "email" in data_to_update and data_to_update["email"] != user.email:
                existing_user = await AuthService(self.db).get_user_by_email_or_none(data_to_update["email"])
                if existing_user:
                    logger.error(f"Email already in use, choose another email")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already in use, choose another email"
                    )
                
            # Validate username is unique
            exiting_username = await self.db.execute(
                select(User).where(
                    User.username == data_to_update["username"],
                    User.id != user_id
                )
            )
            existing_user_with_username = exiting_username.scalars().first()
            if existing_user_with_username:
                logger.error(f"Username already in username, choose another username")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already in username, choose another username"
                )
            
            # Update user information
            for field, value in data_to_update.items():
                setattr(user, field, value)

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed for user_id={user_id}: {db_exc}")
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            
            await self.db.refresh(user)
            return user

        except HTTPException:
            raise
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error during user update for user_id={user_id}: {e}")
            raise ValueError("Unexpected error during user patching")

    async def update_password(
            self, 
            user_id: int, 
            new_password: UserPasswordUpdate
        ) -> User:
        """Update user password and return updated user object.
        
        Args:
            user_id (int): ID of user to update.
            new_password (UserPasswordUpdate): Pydantic model containing the new password.
            
        Returns:
            Updated User object.
            
        Raises:
            HTTPException: If user not found.
            ValueError: On unexpected internal errors.
        """
        try:
            # Get user from database
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                logger.error(f"User not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
        
            # Hash the new password
            hashed_password = AuthService(self.db).get_password_hash(new_password)
        
            # Update and commit
            user.hashed_password = hashed_password
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed for user_id={user_id}: {db_exc}")
                raise ValueError(f"Database commit failed: {str(db_exc)}")  
            
            await self.db.refresh(user)
            return user
        
        except HTTPException:
            raise
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error updating password for user_id={user_id}: {e}")
            raise ValueError("Unexpected error during password update")
    
    async def delete_user(
            self, 
            user_id: int
        ) -> None:
        """
        Permanently delete a user account and related profile.
        
        Flow:
        1. Verify user exists.
        2. Delete associated profile (if exists).
        3. Delete user record.
        4. Commit transaction.
        
        Args:
            user_id (int): ID of the user to delete.
            
        Raises:
            HTTPException: If user not found.
            ValueError: On unexpected internal errors.
        """
        try:
            # Get the user with profile eagerly loaded
            result = await self.db.execute(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.profile))
            )
            user = result.scalars().first()
            if not user:
                logger.error(f"User not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Delete associated profile if exists
            if user.profile:
                await self.db.delete(user.profile)
            
            # Delete the user record
            await self.db.delete(user)
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed while deleting user_id={user_id}: {db_exc}")
                raise ValueError(f"Failed to commit user deletion: {str(db_exc)}")  
            
        except HTTPException:
            raise
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error during deletion of user_id={user_id}: {e}")
            raise ValueError("Unexpected error during user deletion") from e

    async def mark_email_as_verified(
            self, 
            email: str
        ) -> None:
        """
        Mark a user's email as verified in the database.
        
        Args:
            email: Email address to verify

        Raises:
            HTTPException: If no user was found with the provided email.
            ValueError: On unexpected internal errors or DB commit failures.
        """
        try:
            # Find user and check if is already verified
            result = await self.db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalars().first()
            if not user:
                logger.error(f"No user found with email")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No user found with email"
                )
            if user.email_verified:
                logger.error(f"User already verified")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already verified"
                )

            # Proceed to update
            user.email_verified = True
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed while marking email as verified for email={email}: {db_exc}")
                raise ValueError(f"Failed to commit user deletion: {str(db_exc)}") 
             
        except HTTPException:
            raise
        except ValueError:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error while marking email as verified for email={email}: {e}")
            raise ValueError("Unexpected error during marking as verified") from e
        
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