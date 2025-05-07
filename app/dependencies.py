"""
Application Dependency Injections
===============================

Dependency definitions for:
- /users/me
"""

from fastapi import Depends
from app.services.auth import AuthService
from fastapi.security import OAuth2PasswordBearer

# OAuth2 Password Bearer Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(auth_service: AuthService = Depends(), token: str = Depends(oauth2_scheme)):
    """
    Dependency for retrieving the current authenticated user.

    Flow:
    1. Extracts JWT from Authorization header
    2. Validates token via AuthService
    3. Returns active user

    Args:
        auth_service: Injected AuthService instance
        token: JWT from request header

    Returns:
        UserInDB: Authenticated user Pydantic model

    Raises:
        HTTPException: 
            - 401 if token is invalid
            - 400 if user inactive
    """
    return await auth_service.get_current_active_user(token)