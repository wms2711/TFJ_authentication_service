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
    ADMIN ONLY: Get all users in the system
    
    Returns:
        List of all users (including other admins and employers)
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
    admin_service = AdminService(db)
    return await admin_service.update_user(user_id, user_data, current_user)