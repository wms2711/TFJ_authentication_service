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
from pathlib import Path

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
        
        # Get user profile
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        db_profile = result.scalar_one_or_none()
        if not db_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User profile not found, please create user profile first"
            )
        
        # Create user-specific upload directory
        user_upload_dir = Path(upload_dir) / str(user_id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uuid.uuid4().hex}{file_ext}"
        file_path = user_upload_dir / unique_filename

        try:
            # Save file asynchronously
            async with aiofiles.open(file_path, 'wb') as buffer:
                content = await file.read()
                await buffer.write(content)

            # Create new resume entry
            new_resume = {
                "id": str(uuid.uuid4()),
                "url": str(file_path),
                "filename": file.filename,
                "size": len(content),
                "type": file_ext[1:],
                "uploaded_at": datetime.utcnow().isoformat(),
                "is_current": True
            }

            # Initialize resumes array if doesn't exist and mark all other resumes as not current active
            if not db_profile.resumes:
                db_profile.resumes = []
            for resume in db_profile.resumes:
                resume["is_current"] = False

            # If more than 10 most recent resume, remove older resumes
            if len(db_profile.resumes) >= 10:
                removed_resume = db_profile.resumes.pop(0)
                old_file_path = Path(removed_resume["url"])
                if old_file_path.exists():
                    old_file_path.unlink()

            db_profile.resumes.append(new_resume)
            db_profile.current_resume_id = new_resume["id"]
            db_profile.updated_at = datetime.utcnow()
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                # Clean up the uploaded file if DB commit failed
                if file_path.exists():
                    file_path.unlink()
                logger.exception(f"Database commit failed for user_id {user_id}: {db_exc}", exc_info=True)
                raise HTTPException(status_code=500, detail="Database commit failed")
            await self.db.refresh(db_profile)
        
            return {
                "message": "Resume uploaded successfully",
                "resume_id": new_resume["id"],
                "filename": new_resume["filename"],
                "url": new_resume["url"],
                "is_current": True,
                "uploaded_at": new_resume["uploaded_at"]
            }
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error uploading resume {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error uploading resume")

    async def delete_resume(
            self, 
            user_id: int,
            resume_id: str
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
            if not db_profile or not db_profile.resumes:
                return False
        
            # Find resume to delete
            resume_to_delete = next((r for r in db_profile.resumes if r["id"] == resume_id), None)
            if not resume_to_delete:
                return False
            
            # Delete file
            try:
                if os.path.exists(resume_to_delete["url"]):
                    os.unlink(resume_to_delete["url"])
            except Exception as e:
                logger.error(f"Failed to delete resume file: {str(e)}")

        
            # Update profile
            new_resumes = [r for r in db_profile.resumes if r["id"] != resume_id]
            
            if db_profile.current_resume_id == resume_id:
                db_profile.current_resume_id = new_resumes[0]["id"] if new_resumes else None
                if new_resumes:
                    new_resumes[0]["is_current"] = True
            db_profile.resumes = new_resumes
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