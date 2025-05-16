"""
Authentication Router
=====================

Handles all authentication-related endpoints including:
- User login (JWT token generation)
- Token refresh
- Token validation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.database.session import get_db, async_get_db
from app.schemas.token import Token
from app.services.auth import AuthService
from app.services.user import UserService
from app.database.models.user import User
from app.config import settings

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
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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

# To implement:
# - POST /auth/forgot-password for registered users that forgot password and wants to reset it, generate one time-use JWT and sends an email with a link, to set new password (/auth/reset-password).
# - POST /auth/send-verification for new sign-ups and need to verify their email address, send email verification link.
# - POST /auth/reset-password to reset password.
