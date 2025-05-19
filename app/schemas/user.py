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

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class UserPasswordUpdate(BaseModel):
    new_password: str