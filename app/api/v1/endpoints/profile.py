"""
Profile Management Router
=========================

Handles all profile-related endpoints including:
- Profile creation and retrieval
- Resume upload, download, and deletion
- Profile updates
"""


from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.services.profile import ProfileService
from app.schemas.profile import (
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileInDB,
    ResumeItemResponse
)
from app.database.session import get_db, async_get_db
from app.services.auth import AuthService
from app.database.models.user import User
from app.dependencies import get_current_user

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=UserProfileInDB)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Get current user's complete profile.
    
    Flow:
    1. Validates JWT from Authorization header.
    2. Retrieves profile for authenticated user.
    3. Returns full profile data.
    
    Args:
        current_user (User): Authenticate and automatically inject user details from JWT.
        db (AsyncSession): Active async database session.
        
    Returns:
        UserProfileInDB: Complete profile information.
        
    Raises:
        HTTPException: 404 if profile not found.
    """
    profile_service = ProfileService(db)
    profile = await profile_service.get_profile_by_user_id(current_user.id)
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
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Create a new profile for current user.
    
    Flow:
    1. Validates user doesn't already have a profile.
    2. Creates new profile with provided data.
    3. Returns created profile.
    
    Args:
        profile_data (UserProfileCreate): Basic profile information.
        current_user (User): Authenticate and automatically inject user details from JWT.
        db (AsyncSession): Active async database session.
        
    Returns:
        UserProfileInDB: Newly created profile.
        
    Raises:
        HTTPException: 
            - 400 if profile already exists.
            - 401 if not authenticated.
    """
    profile_service = ProfileService(db)
    existing_profile = await profile_service.get_profile_by_user_id(current_user.id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists"
        )
    
    return await profile_service.create_profile(current_user.id, profile_data)

@router.put("/me", response_model=UserProfileInDB)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Update current user's profile.
    
    Flow:
    1. Validates profile exists.
    2. Updates fields with provided data.
    3. Returns updated profile.
    
    Args:
        profile_data (UserProfileCreate): Basic profile information.
        current_user (User): Authenticate and automatically inject user details from JWT.
        db (AsyncSession): Active async database session.
        
    Returns:
        UserProfileInDB: Updated profile information.
        
    Raises:
        HTTPException: 
            - 404 if profile not found.
            - 401 if not authenticated.
    """
    profile_service = ProfileService(db)
    updated_profile = await profile_service.update_profile(current_user.id, profile_data)
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return updated_profile

@router.get("/me/resumes", response_model=List[ResumeItemResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Retrieve all resumes uploaded by the currently authenticated user.

    - Returns a list of resume metadata entries.
    - The latest (current) resume is marked with `is_current = True`.

    Requires:
        - Authenticated user.

    Returns:
        List[ResumeItemResponse]: A list of resume metadata dictionaries containing:
            - resume_id
            - filename
            - url
            - size
            - type
            - uploaded_at
            - is_current
    """
    service = ProfileService(db)
    return await service.get_resumes(current_user.id)

@router.post("/me/resume")
async def upload_my_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Upload resume for current user.
    
    Flow:
    1. Validates file type (PDF/DOC/DOCX).
    2. Saves file to server storage.
    3. Updates profile with resume metadata.
    
    Args:
        file (UploadFile): Resume file to upload.
        current_user (User): Authenticate and automatically inject user details from JWT.
        db (AsyncSession): Active async database session.
        
    Returns:
        dict: Upload result with file metadata.
        
    Raises:
        HTTPException:
            - 400 for invalid file types.
            - 401 if not authenticated.
            - 500 for upload failures.
    """
    if not file.filename.lower().endswith(('.pdf', '.doc', '.docx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOC, and DOCX files are allowed"
        )
    
    profile_service = ProfileService(db)
    upload_dir = "uploads/resumes"
    return await profile_service.upload_resume(current_user.id, file, upload_dir)


@router.delete("/me/resume/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Delete current user's resume that user specifies
    
    Flow:
    1. Removes specific resume file from storage.
    2. Clears or updates resume metadata from profile.
    
    Args:
        current_user (User): Authenticate and automatically inject user details from JWT.
        db (AsyncSession): Active async database session.
        
    Returns:
        None: 204 No Content on success.
        
    Raises:
        HTTPException:
            - 404 if no resume exists.
            - 401 if not authenticated.
    """
    profile_service = ProfileService(db)
    if not await profile_service.delete_resume(current_user.id, resume_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile / Resume not found"
        )
    return None


@router.get("/me/resume/{resume_id}")
async def download_my_resume(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    """
    Download current user's resume
    
    Flow:
    1. Checks if resume exists
    2. Streams file directly to client
    
    Args:
        current_user: Authenticated user from JWT
        db: Active database session
        
    Returns:
        FileResponse: Binary file stream with proper headers
        
    Raises:
        HTTPException:
            - 404 if no resume exists
            - 401 if not authenticated
    """
    profile_service = ProfileService(db)
    resume = await profile_service.get_resume_by_id(current_user.id, resume_id)
    return FileResponse(
        path=resume["url"],
        filename=resume["filename"],
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={resume['filename']}"}
    )