from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.services.profile import ProfileService
from app.schemas.profile import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileInDB,
    ResumeUploadResponse
)
from app.database.session import get_db
from app.services.auth import AuthService
from app.database.models.user import User
from app.dependencies import get_current_user
from fastapi.security import OAuth2PasswordBearer

# Initialize OAuth2 scheme
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=UserProfileInDB)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile_service = ProfileService(db)
    profile = profile_service.get_profile_by_user_id(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return profile


@router.post("/me", response_model=UserProfileInDB)
async def create_my_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile_service = ProfileService(db)
    existing_profile = profile_service.get_profile_by_user_id(current_user.id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )
    
    return profile_service.create_profile(current_user.id, profile_data)


@router.put("/me", response_model=UserProfileInDB)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile_service = ProfileService(db)
    updated_profile = profile_service.update_profile(current_user.id, profile_data)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return updated_profile


@router.post("/me/resume")
async def upload_my_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOC, and DOCX files are allowed"
        )
    
    profile_service = ProfileService(db)
    upload_dir = "uploads/resumes"
    try:
        result = await profile_service.upload_resume(current_user.id, file, upload_dir)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading resume: {str(e)}"
        )


@router.delete("/me/resume", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile_service = ProfileService(db)
    if not profile_service.delete_resume(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    return None


@router.get("/me/resume")
async def download_my_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile_service = ProfileService(db)
    resume_path = profile_service.get_resume_path(current_user.id)
    if not resume_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    
    # In production, you would return a FileResponse:
    # from fastapi.responses import FileResponse
    # return FileResponse(resume_path, filename=profile.resume_original_filename)
    
    return {"resume_path": resume_path}