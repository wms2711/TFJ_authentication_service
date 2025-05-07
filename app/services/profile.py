from typing import Optional
from sqlalchemy.orm import Session
from app.database.models.profile import UserProfile
from app.schemas.profile import UserProfileCreate, UserProfileUpdate, UserProfileInDB
from fastapi import UploadFile
import os
import uuid
from datetime import datetime


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_profile_by_user_id(self, user_id: int) -> Optional[UserProfileInDB]:
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        return profile

    def create_profile(self, user_id: int, profile_data: UserProfileCreate) -> UserProfileInDB:
        now = datetime.utcnow()
        db_profile = UserProfile(
            user_id=user_id,
            created_at=now,
            updated_at=now,
            **profile_data.dict(exclude_unset=True)
            )
        self.db.add(db_profile)
        self.db.commit()
        self.db.refresh(db_profile)
        return db_profile

    def update_profile(self, user_id: int, profile_data: UserProfileUpdate) -> Optional[UserProfileInDB]:
        db_profile = self.get_profile_by_user_id(user_id)
        if not db_profile:
            return None

        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_profile, field, value)

        db_profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_profile)
        return db_profile

    def upload_resume(self, user_id: int, file: UploadFile, upload_dir: str) -> dict:
        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        # Update profile with resume info
        db_profile = self.get_profile_by_user_id(user_id)
        if not db_profile:
            return {"message": "Profile not found", "resume_url": None, "filename": None}
        
        # If there's an old resume, delete it
        if db_profile.resume_url and os.path.exists(db_profile.resume_url):
            try:
                os.remove(db_profile.resume_url)
            except:
                pass
        
        # Update profile
        db_profile.resume_url = file_path
        db_profile.resume_original_filename = file.filename
        self.db.commit()
        
        return {
            "message": "Resume uploaded successfully",
            "resume_url": file_path,
            "filename": file.filename
        }

    def delete_resume(self, user_id: int) -> bool:
        db_profile = self.get_profile_by_user_id(user_id)
        if not db_profile or not db_profile.resume_url:
            return False
        
        # Delete file
        if os.path.exists(db_profile.resume_url):
            try:
                os.remove(db_profile.resume_url)
            except:
                pass
        
        # Update profile
        db_profile.resume_url = None
        db_profile.resume_original_filename = None
        self.db.commit()
        return True

    def get_resume_path(self, user_id: int) -> Optional[str]:
        db_profile = self.get_profile_by_user_id(user_id)
        if not db_profile or not db_profile.resume_url:
            return None
        return db_profile.resume_url