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
        Upload a resume file and associate it with a user's profile.

        - Stores the resume in a user-specific directory with a unique filename.
        - Replaces any existing current resume.
        - Maintains only the 10 most recent resumes.

        Args:
            user_id (int): ID of the user uploading the resume.
            file (UploadFile): The uploaded resume file.
            upload_dir (str): Base directory where resumes should be saved.

        Returns:
            dict: Metadata of the uploaded resume, including resume ID, file path, and upload timestamp.

        Raises:
            HTTPException:
                - 400: If the uploaded file is invalid.
                - 404: If the user profile does not exist.
                - 500: On file write failure, database commit failure, or unexpected error.
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
        Delete a specific resume associated with a user's profile.

        - Deletes the file from the filesystem.
        - Removes the resume metadata from the user's profile.
        - Updates the `current_resume_id` field if the current resume is deleted.

        Args:
            user_id (int): ID of the user.
            resume_id (str): ID of the resume to be deleted.

        Returns:
            bool: True if deletion is successful, False otherwise.

        Raises:
            HTTPException:
                - 500: On database commit failure or unexpected error.
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
        
    async def get_resumes(
            self, 
            user_id: int
        ) -> list:
        """
        Retrieve all resumes associated with a user's profile.

        Args:
            user_id (int): ID of the user.

        Returns:
            list: A list of resume dictionaries.

        Raises:
            HTTPException: 500 if a database error occurs.
        """
        try:
            profile = await self.get_profile_by_user_id(user_id)
            return profile.resumes if profile else []
        
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to retrieve resumes for user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error retrieving resumes")
        
    async def get_resume_by_id(
            self, 
            user_id: int, 
            resume_id: str
        ) -> dict:
        """
        Retrieve a specific resume by ID and verify the file exists.

        Args:
            user_id (int): ID of the user.
            resume_id (str): UUID of the resume.

        Returns:
            dict: The resume metadata.

        Raises:
            HTTPException: 
                - 404 if profile, resumes, or specific resume not found.
                - 500 if a database error or file check fails.
        """
        try:
            profile = await self.get_profile_by_user_id(user_id)
            if not profile or not profile.resumes:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Profile / Resumes found for user"
                )
            resume = next((r for r in profile.resumes if r["id"] == resume_id), None)
            if not resume:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resume not found"
                )
        
            if not os.path.exists(resume["url"]):
                logger.error(f"File not found at path: {resume['url']}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resume file not found on server"
                )
            return resume

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error retrieving resume {resume_id} for user_id {user_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error retrieving resume")
        
    async def set_current_resume(
            self, 
            user_id: int, 
            resume_id: str
        ) -> Optional[dict]:
        """
        Set a specific resume as the current active resume for a user's profile.

        Args:
            user_id (int): The ID of the user whose resume is being set.
            resume_id (str): The ID of the resume to be marked as current.

        Returns:
            Optional[dict]: A dictionary containing the details of the updated current resume:
                - id (str): Resume ID.
                - filename (str): Name of the uploaded resume file.
                - url (str): Path/URL to the stored resume.
                - uploaded_at (datetime): Timestamp of when the resume was uploaded.
                - is_current (bool): Indicates this is the active resume (always True here).

        Raises:
            HTTPException:
                - 404: If the user profile or resume is not found.
                - 500: On database commit failure or unexpected errors.
        """
        try:
            # Find profile
            db_profile = await self.get_profile_by_user_id(user_id)
            if not db_profile or not db_profile.resumes:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Profile / Resumes found for user"
                )

            # Verify resume exists in profile
            target_resume = next((r for r in db_profile.resumes if r["id"] == resume_id), None)
            if not target_resume:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resume not found"
                )
            
            # Update all resume
            updated_resumes = []
            for resume in db_profile.resumes:
                resume_copy = dict(resume)  # Create a copy to modify
                resume_copy["is_current"] = (resume["id"] == resume_id)
                updated_resumes.append(resume_copy)

            db_profile.resumes = updated_resumes
            db_profile.current_resume_id = resume_id
            db_profile.updated_at = datetime.utcnow()

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.exception(
                    f"Database commit failed setting current resume for user_id {user_id}: {db_exc}",
                    exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database commit failed"
                )
            await self.db.refresh(db_profile)
            return {
                "id": target_resume["id"],
                "filename": target_resume["filename"],
                "url": target_resume["url"],
                "uploaded_at": target_resume["uploaded_at"],
                "is_current": True,
            }
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                f"Unexpected error setting current resume for user {user_id}: {e}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error setting current resume"
            )