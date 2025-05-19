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
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str