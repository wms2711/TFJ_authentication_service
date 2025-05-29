from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database.session import async_get_db
from app.schemas.notification import NotificationCreate, NotificationInDB
from app.services.notification import NotificationService
from app.dependencies import get_current_user
from app.database.models.user import User

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/notification",
    tags=["notification"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=NotificationInDB)
async def create_notification(
    notification_payload: NotificationCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    notification_service = NotificationService(db)
    return await notification_service.create_notification(notification_payload, current_user)