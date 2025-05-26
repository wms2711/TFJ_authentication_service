"""
User Data Schemas
================

Defines the data structures for user account handling across different layers:
1. API request/response formats
2. Database model representations
3. Internal service transfers
"""

from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    """
    Core user attributes shared across all schemas.
    
    Used as base for:
    - User creation (registration)
    - User responses (profile data)
    - Database representations
    
    Fields:
        username (str): Unique account identifier
        email (EmailStr): Validated email address
        full_name (Optional[str]): Display name (optional)
    """
    username: str
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    """
    User registration schema containing password.
    
    Used exclusively for:
    - POST /users registration endpoint
    
    Extends:
        UserBase with password field
    
    Security:
        Password is hashed before storage
    """
    password: str

class UserInDB(UserBase):
    """
    Complete user representation including system fields.
    
    Used for:
    - Returning model
    """
    id: int
    is_active: bool
    is_employer: bool
    is_admin: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    """
    Schema for updating user profile data.
    
    Used in:
    - PATCH /users/{id} or /users/me endpoints
    
    Attributes:
        username (Optional[str]): New username (if being updated)
        email (Optional[str]): New email address (if being updated)
        full_name (Optional[str]): New display name (optional)
        is_active (Optional[bool]): Account activation status (admin-controlled)
    
    Notes:
        Only fields provided in the request will be updated.
    """
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserPasswordUpdate(BaseModel):
    """
    Schema for updating a user's password.
    
    Used in:
    - PUT /users/{id}/password
    - User-initiated password change workflows
    
    Attributes:
        new_password (str): The new password to be set. Should meet application-defined strength criteria.
        
    Security:
        Password is expected to be hashed before persistence.
    """
    new_password: str

class UserVerificationRequest(BaseModel):
    """
    Schema for verification of user.
    
    Used in:
    - GET /users/verify-email
    - For new sign-ups who needs identity verification
    
    Attributes:
        token (str): The new sign-ups verification token sent to the user's email.
    """
    token: str