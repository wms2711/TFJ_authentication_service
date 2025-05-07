"""
Authentication Router
====================

Handles all authentication-related endpoints including:
- User login (JWT token generation)
- Token refresh
- Token validation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.database.session import get_db
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
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and generate access token
    
    Flow:
    1. Receives username/password via form data
    2. Validates credentials against database
    3. Returns JWT token if successful
    
    Args:
        form_data: OAuth2 standard username/password form
        db: Active database session
        
    Returns:
        Token: JWT access token and type
        
    Raises:
        HTTPException: 401 if invalid credentials
    """
    auth_service = AuthService(db)

    # Authenticate user credentials
    user = auth_service.authenticate_user(form_data.username, form_data.password)
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
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Generate new access token using valid existing token
    
    Flow:
    1. Validates current token
    2. Issues new token with fresh expiration
    
    Args:
        token: Current valid JWT from Authorization header
        db: Active database session
        
    Returns:
        Token: New JWT access token
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
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Validate token and return user information
    
    Flow:
    1. Checks token validity
    2. Verifies user exists and is active
    3. Returns validation status
    
    Args:
        token: JWT from Authorization header
        db: Active database session
        
    Returns:
        dict: Token validity and username
    """

    auth_service = AuthService(db)

    # Validate token and get current user
    current_user = await auth_service.get_current_active_user(token)
    return {"valid": True, "user": current_user.username}

# To implement:
# - POST /auth/forgot-password for registered users that forgot password and wants to reset it, generate one time-use JWT and sends an email with a link, to set new password (/auth/reset-password).
# - POST /auth/send-verification for new sign-ups and need to verify their email address, send email verification link.
# - POST /auth/reset-password to reset password.
