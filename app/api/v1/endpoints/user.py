"""
User Management Router
======================

Handles all user-related endpoints including:
- User registration
- Current user profile retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db, async_get_db
from app.schemas.user import UserInDB, UserCreate, UserUpdate, UserVerificationRequest
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.email import EmailService
from slowapi.util import get_remote_address
from slowapi import Limiter
from app.dependencies import get_user

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(prefix="/users", tags=["users"])

# Define limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=UserInDB)
@limiter.limit("3/minute")
async def create_user(
    request: Request,
    user: UserCreate, 
    background_tasks: BackgroundTasks,
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
):
    # TODO: request payload has additional unknown field
    """
    Register a new user.
    
    Flow:
    1. Receives user registration data.
    2. Validates uniqueness of username/email.
    3. Hashes password.
    4. Creates user record in database.
    
    Args:
        user (UserCreate): User creation data (username, email, password, etc.).
        db (AsyncSession): Active async database session.
        
    Returns:
        UserInDB: Created user information (excluding password).
        
    Raises:
        HTTPException: 400 if username/email already exists.
    """
    user_service = UserService(db)
    auth_service = AuthService(db)
    email_service = EmailService()

    # Create user
    created_user = await user_service.create_user(user)

    # Generate verification token and send email
    verification_token = auth_service.generate_verification_token(created_user.email)

    # # Send email in background (production)
    # background_tasks.add_task(
    #     email_service.send_verification_email,
    #     email=created_user.email,
    #     token=verification_token
    # )
    await email_service.send_verification_email(created_user.email, verification_token)

    return created_user

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_user)):
    """
    Get current authenticated user's profile.
    
    Flow:
    1. Validates JWT from Authorization header.
    2. Retrieves current user from database.
    3. Returns user profile.
    
    Args:
        current_user (User): Authenticate and automatically inject user details from JWT.
        
    Returns:
        UserInDB: Authenticated user's profile.
    """
    return current_user

@router.patch("/me", response_model=UserInDB)
async def update_user_me(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_user),
    db: AsyncSession = Depends(async_get_db),
):
    # TODO: do not check inactive users
    """
    Update current authenticated user's profile.
    
    Flow:
    1. Validates JWT from Authorization header.
    2. Receives partial update data.
    3. Validates and applies updates.
    4. Returns updated user profile.
    
    Args:
        user_update: Partial user data to update.
        current_user: Authenticated user from JWT.
        db: Async database session.
        
    Returns:
        Updated user profile.
        
    Raises:
        HTTPException: 400 if validation fails (e.g., email already in use).
    """
    user_service = UserService(db)
    try:
        updated_user = await user_service.update_user(
            user_id=current_user.id,
            update_data=user_update
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_me(
    current_user: UserInDB = Depends(get_user),
    db: AsyncSession = Depends(async_get_db),
    auth_service: AuthService = Depends()
):
    """
    Delete current user's account and profile while preserving applications.
    
    Flow:
    1. Verify authentication.
    2. Delete profile (if exists).
    3. Delete user account.
    4. Cleanup auth tokens.
    5. Send confirmation.
    
    Security:
    - Only affects currently authenticated user.
    - Atomic transaction ensures all-or-nothing deletion.
    - Preserves application records as per business requirements.
    """
    user_service = UserService(db)
    try:
        # Perform the deletion (both user and profile)
        await user_service.delete_user(current_user.id)
        
        # Cleanup authentication artifacts
        # await auth_service.revoke_all_user_tokens(current_user.id)
        
        # Send confirmation email
        # await auth_service.send_account_deletion_email(current_user.email)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed"
        )
    
@router.get("/verify-email")
@limiter.limit("5/minute")
async def verify_email(
    request: Request,
    form_data: UserVerificationRequest,
    db: AsyncSession = Depends(async_get_db)
):
    """
    Verify user's email using the verification token.
    
    Flow:
    1. Decodes and validates the token
    2. Marks email as verified in database
    3. Returns success message
    
    Args:
        token: Verification token from email link
        
    Returns:
        JSON response with success message
        
    Raises:
        HTTPException: 400 if token is invalid
    """
    auth_service = AuthService(db)
    email = auth_service.verify_email_token(form_data.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user_service = UserService(db)
    await user_service.mark_email_as_verified(email)

    return {"message": "Email successfully verified"}