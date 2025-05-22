"""
Authentication Router
=====================

Handles all authentication-related endpoints including:
- User login (JWT token generation)
- Token refresh
- Token validation
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.database.session import get_db, async_get_db
from app.schemas.token import Token, ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth import AuthService
from app.services.user import UserService
from app.services.email import EmailService
from app.database.models.user import User
from app.config import settings
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize router with prefix and tags for OpenAPI docs
router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    # db: Session = Depends(get_db)
    db: AsyncSession = Depends(async_get_db)
):
    """
    Authenticate user and return a JWT access token.

    Process:
    1. Accepts username and password via form data.
    2. Verifies user credentials against the database.
    3. Returns a signed JWT access token if authentication is successful.

    Args:
        form_data (OAuth2PasswordRequestForm): Standard form containing username and password.
        db (AsyncSession): Active async database session.

    Returns:
        Token: JWT access token and token type ("bearer").

    Raises:
        HTTPException: 401 Unauthorized if authentication fails.
    """
    auth_service = AuthService(db)

    # Authenticate user credentials
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    
    # Generate token with expiration
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Refresh an existing JWT access token.

    Process:
    1. Validates the current access token.
    2. If valid, generates and returns a new token with fresh expiration.

    Args:
        token (str): Current JWT from Authorization header.
        db (AsyncSession): Active async database session.

    Returns:
        Token: Refreshed JWT access token and token type.
    """
    auth_service = AuthService(db)

    # Validate token and get current user
    current_user = await auth_service.get_current_active_user(token)
    
    # Generate new token with expiration
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": current_user.username}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/check-token")
async def check_token(
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Validate a JWT access token and return associated user info.

    Process:
    1. Verifies token authenticity and user status.
    2. Returns the username and token validity status.

    Args:
        token (str): JWT from the Authorization header.
        db (AsyncSession): Active async database session.

    Returns:
        dict: Token validation result and username.
    """
    auth_service = AuthService(db)

    # Validate token and get current user
    current_user = await auth_service.get_current_active_user(token)
    return {"valid": True, "user": current_user.username}

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(async_get_db)
):
    """
    Initiate password reset process.
    
    1. Checks if email exists in system.
    2. Generates time-limited reset token (expires in 15 mins).
    3. Sends email with reset link containing token.
    
    Args:
        request: Contains user's email address.
        background_tasks: FastAPI background tasks for sending email async.
        db: Async database session.
    
    Returns:
        Message confirming reset email was sent (even if email doesn't exist).
    """
    auth_service = AuthService(db)
    email_service = EmailService()

    # Check if user exists
    user = await auth_service.get_user_by_email(request.email)
    # Generate reset token
    reset_token = auth_service.create_reset_token(
        email=user.email,
        expires_delta=timedelta(minutes=15)
    )
    
    # # Send email in background (production)
    # background_tasks.add_task(
    #     email_service.send_password_reset_email,
    #     email=user.email,
    #     token=reset_token
    # )
    success = await email_service.send_password_reset_email(user.email, reset_token)
    if not success:
        logger.error(f"Failed to send reset email to {user.email}")

    return {"message": "Password reset link sent to your email"}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(async_get_db)
):
    """
    Reset user password using valid reset token.
    
    Flow:
    1. Verifies the reset token is valid and not expired.
    2. Checks if new password meets complexity requirements.
    3. Updates user's password in database.
    4. Invalidates the used token.
    
    Args:
        request: Contains reset token and new password.
        db: Async database session.
    
    Returns:
        Success message if password was reset.
        
    Raises:
        HTTPException: 400 if token is invalid/expired or password fails validation.
    """
    auth_service = AuthService(db)
    user_service = UserService(db)
    try:
        # Verify token and get email
        email = auth_service.verify_reset_token(request.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired token"
            )

        # TODO optional: Validate user password (e.g. reject less than 8 char), this part can be done in frontend?

        # Get user by email
        user = await auth_service.get_user_by_email(email)
        
        # Update password - modified to use user_id instead of email
        await user_service.update_password(
            user_id=user.id,
            new_password=request.new_password
        )

        # TODO: one-time password reset, won't trigger reset password twice
    except HTTPException:
        raise  # Re-raise existing HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting password"
        )
