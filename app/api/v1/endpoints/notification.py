"""
Notification Management Router
==============================

Handles all user-facing notifications, including:
- Creating notifications (Admin/Employer only)
- Viewing notifications (User)
- Marking notifications as read (User)

Security:
---------
- Only Admins and Employers can create notifications.
- Any authenticated user can view and mark their own notifications.
"""

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
    """
    ADMIN / EMPLOYER ONLY: Create a new notification for a user.

    Flow:
    1. Authenticates current user.
    2. Verifies user is either admin or employer.
    3. Creates a notification targeted at a specific user.

    Args:
        notification_payload (NotificationCreate): Contains target user ID, title, and message.
        db (AsyncSession): Active async database session.
        current_user (User): Current authenticated user object.

    Returns:
        NotificationInDB: The created notification object.

    Raises:
        HTTPException:
            - 403 if the user is not authorized or user is inactive.
            - 400 if payload validation fails.
            - 404 if the user is not found.
            - 500 if other errors.
    """
    notification_service = NotificationService(db)
    return await notification_service.create_notification(notification_payload, current_user)

@router.get("/", response_model=List[NotificationInDB])
async def get_notifications(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch all notifications for the currently logged-in user.

    Flow:
    1. Authenticates current user.
    2. Retrieves all notifications where user is the target.

    Args:
        db (AsyncSession): Active async database session.
        current_user (User): Current authenticated user object.

    Returns:
        List[NotificationInDB]: All notifications for the current user.

    Raises:
        HTTPException: 401 if authentication fails.
    """
    notification_service = NotificationService(db)
    return await notification_service.get_notifications_for_user(current_user)

@router.patch("/{notif_id}", response_model=NotificationInDB)
async def mark_notification_as_read(
    notif_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific notification as read.

    Flow:
    1. Authenticates current user.
    2. Verifies notification belongs to current user.
    3. Marks the notification as read.

    Args:
        notif_id (int): Notification ID to mark as read.
        db (AsyncSession): Active async database session.
        current_user (User): Current authenticated user object.

    Returns:
        NotificationInDB: The updated notification object.

    Raises:
        HTTPException:
            - 403 if user is not the recipient.
            - 404 if notification not found.
            - 500 if other errors.
    """
    notification_service = NotificationService(db)
    return await notification_service.mark_as_read(notif_id, current_user)