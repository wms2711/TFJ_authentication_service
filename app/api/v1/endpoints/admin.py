"""
Admin Management Router
=======================

Handles all admin-only endpoints, including:
- Retrieving all users
- Updating user profiles with admin privileges (admin cannot modify itself or other admins)

Security:
---------
These endpoints are restricted to authenticated admin users only.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database.session import async_get_db
from app.schemas.user import UserInDB, UserUpdateAdmin
from app.services.admin import AdminService
from app.database.models.user import User
from app.dependencies import get_current_user

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

@router.get("/users", response_model=List[UserInDB])
async def get_all_users(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ADMIN ONLY: Get all users in the system.
    
    Flow:
    1. Authenticates current user.
    2. Validates admin privileges.
    3. Retrieves and returns all users from the database.
    
    Args:
        db (AsyncSession): Active async database session.
        current_user (User): Current authenticated user object.
    
    Returns:
        List[UserInDB]: List of all users including admins and employers.
    
    Raises:
        HTTPException: 403 if user is not an admin.
    """
    admin_service = AdminService(db)
    return await admin_service.get_all_users(current_user)

@router.patch("/users/{user_id}", response_model=UserInDB)
async def update_user(
    user_id: int,
    user_data: UserUpdateAdmin,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ADMIN ONLY: Update a specific user's profile.
    
    Flow:
    1. Authenticates current user.
    2. Validates admin privileges.
    3. Applies updates to the specified user.
    
    Args:
        user_id (int): ID of the user to update.
        user_data (UserUpdateAdmin): Fields to update (is_active, is_admin, etc.)
        db (AsyncSession): Active async database session.
        current_user (User): Current authenticated user object.
    
    Returns:
        UserInDB: Updated user profile.
    
    Raises:
        HTTPException: 
            - 403 if user is not an admin.
            - 404 if target user not found.
            - 400 if validation fails.
    """
    admin_service = AdminService(db)
    return await admin_service.update_user(user_id, user_data, current_user)