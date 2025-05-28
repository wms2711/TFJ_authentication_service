"""
Profile Management Service
==========================

Handles all business logic related to user profile operations:
- Create, read, and update user profile
- Upload and delete resume files
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.profile import UserProfile
from app.schemas.profile import UserProfileCreate, UserProfileUpdate, UserProfileInDB
from fastapi import UploadFile, HTTPException, status
import os
import uuid
import aiofiles
from datetime import datetime
from utils.logger import init_logger

# Configure logger
logger = init_logger("ProfileService")

class ProfileService:
    """Main profiling service for managing user profiles."""

    def __init__(self, db: AsyncSession):
        """
        Initialize with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session.
        """
        self.db = db

    async def get_profile_by_user_id(
            self, 
            user_id: int
        ) -> Optional[UserProfileInDB]:
        """
        Retrieve a user's profile by their user ID.
        
        Args:
            user_id (int): ID of the user.
        
        Returns:
            UserProfileInDB | None: Profile data or None if not found.

        Raises:
            HTTPException: 500 if a database error occurs.
        """
        try:
            result = await self.db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(f"Failed to retrieve profile: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error retrieving profile")

    async def create_profile(
            self, 
            user_id: int, 
            profile_data: UserProfileCreate
        ) -> UserProfileInDB:
        """
        Create a new profile for a user.
        
        Args:
            user_id (int): ID of the user.
            profile_data (UserProfileCreate): Profile data to be created.
        
        Returns:
            UserProfileInDB: Created profile.

        Raises:
            HTTPException: 500 if a database error occurs.
        """
        try:
            now = datetime.utcnow()
            db_profile = UserProfile(
                user_id=user_id,
                created_at=now,
                updated_at=now,
                **profile_data.dict(exclude_unset=True)
                )
            self.db.add(db_profile)

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.exception(f"Database commit failed for user_id {user_id}: {db_exc}", exc_info=True)
                raise HTTPException(status_code=500, detail="Database commit failed")

            await self.db.refresh(db_profile)
            return db_profile
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error creating profile for user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error creating profile")

    async def update_profile(
            self, 
            user_id: int, 
            profile_data: UserProfileUpdate
        ) -> Optional[UserProfileInDB]:
        """
        Update an existing user profile.
        
        Args:
            user_id (int): ID of the user.
            profile_data (UserProfileUpdate): Fields to update.
        
        Returns:
            UserProfileInDB | None: Updated profile or None if not found.

        Raises:
            HTTPException: 500 if a database error occurs.
        """
        try:    
            result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            db_profile = result.scalar_one_or_none()
            if not db_profile:
                return None

            update_data = profile_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_profile, field, value)

            db_profile.updated_at = datetime.utcnow()
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.exception(f"Database commit failed for user_id {user_id}: {db_exc}", exc_info=True)
                raise HTTPException(status_code=500, detail="Database commit failed")
            await self.db.refresh(db_profile)
            return db_profile
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error updating profile for user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error updating profile")

    async def upload_resume(
            self, 
            user_id: int, 
            file: UploadFile, 
            upload_dir: str
        ) -> dict:
        """
        Upload and associate a resume file with the user profile.
        
        - Saves the file with a unique name.
        - Replaces existing resume if any.
        
        Args:
            user_id (int): ID of the user.
            file (UploadFile): Uploaded file object.
            upload_dir (str): Directory to store uploaded resumes.
        
        Returns:
            dict: Metadata of uploaded file.

        Raises:
            HTTPException: 
                - 404 if user not found.
                - 500 if a database error occurs.
        """
        # TODO: Safe as binary data in database? (Not recommended as perform bad at scale? might cause slow queries, inflate db size?) 
        # or use storage system (cloud storage?) and save url of resume in database?
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid file upload"
            )

        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        try:
            # Save file asynchronously
            async with aiofiles.open(file_path, 'wb') as buffer:
                content = await file.read()
                await buffer.write(content)
        
            # Update profile
            result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            db_profile = result.scalar_one_or_none()

            if not db_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="User profile not found"
                )

            if db_profile.resume_url and os.path.exists(db_profile.resume_url):
                try:
                    os.remove(db_profile.resume_url)
                except Exception as e:
                    logger.warning(f"Failed to delete resume file at {db_profile.resume_url}: {e}")
            
            db_profile.resume_url = file_path
            db_profile.resume_original_filename = file.filename
            db_profile.updated_at = datetime.utcnow()
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.exception(f"Database commit failed for user_id {user_id}: {db_exc}", exc_info=True)
                raise HTTPException(status_code=500, detail="Database commit failed")
            await self.db.refresh(db_profile)
        
            return {
                "message": "Resume uploaded successfully",
                "resume_url": file_path,
                "filename": file.filename
            }
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error uploading resume {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error uploading resume")

    async def delete_resume(
            self, 
            user_id: int
        ) -> bool:
        """
        Delete the resume file associated with a user's profile.
        
        Args:
            user_id (int): ID of the user.
        
        Returns:
            bool: True if deleted successfully, False otherwise.

        Raises:
            HTTPException: 
                - 500 if a database error occurs.
                - 500 if an unexpected error occurs during resume deletion.
        """
        try:
            db_profile = await self.get_profile_by_user_id(user_id)
            if not db_profile or not db_profile.resume_url:
                return False
        
            # Delete file
            if os.path.exists(db_profile.resume_url):
                try:
                    os.remove(db_profile.resume_url)
                except Exception as e:
                    logger.warning(f"Failed to delete resume file: {str(e)}")
        
            # Update profile
            db_profile.resume_url = None
            db_profile.resume_original_filename = None
            db_profile.updated_at = datetime.utcnow()

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.exception(f"Database commit failed for user_id {user_id}: {db_exc}", exc_info=True)
                raise HTTPException(status_code=500, detail="Database commit failed")
            return True
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error deleting resume {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error deleting resume")