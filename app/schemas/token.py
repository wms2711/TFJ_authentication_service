"""
Authentication Token Schemas
==========================

Defines the data structures for JWT token handling:
1. Token response format
2. Token payload content
"""

from typing import Optional
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    """
    JWT Token response model returned by authentication endpoints.
    
    Used in:
    - /login endpoint response
    - /refresh-token endpoint response
    
    Attributes:
        access_token (str): The encoded JWT string
        token_type (str): Always 'bearer' per OAuth2 spec
        
    Example:
        {
            "access_token": "eyJhbGciOi...",
            "token_type": "bearer"
        }
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Decoded JWT token payload structure.
    
    Used in:
    - /users/me
    
    Attributes:
        username (Optional[str]): Unique user identifier extracted from token
    """
    username: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    """
    Request model for initiating the forgot password process.
    
    Used in:
    - /forgot-password endpoint
    
    Attributes:
        email (EmailStr): The user's registered email address for sending the reset link.
        
    Example:
        {
            "email": "user@example.com"
        }
    """
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """
    Request model for submitting a new password using a reset token.
    
    Used in:
    - /reset-password endpoint
    
    Attributes:
        token (str): The password reset token sent to the user's email.
        new_password (str): The new password the user wants to set.
        
    Example:
        {
            "token": "eyJhbGciOiJIUzI1...",
            "new_password": "newSecurePassword123"
        }
    """
    token: str
    new_password: str