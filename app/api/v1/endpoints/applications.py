"""
Application Management Router
=============================

Handles job application-related operations including:
- Submitting new job applications via Redis stream for ML processing
- Updating application or ML processing status
- Fetching application details
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.services.application import ApplicationService
from app.services.redis import RedisService
from app.dependencies import get_current_user
from app.database.models.user import User
from app.database.models.enums.application import SwipeAction, ApplicationStatus
from app.database.session import get_db, async_get_db

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/application",
    tags=["application"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ApplicationOut)
async def create_application(
    app_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
    redis: RedisService = Depends(RedisService)
):
    """
    Submit a new job application (swipe left or right).

    Process:
    1. Receives job ID from the request body.
    2. Creates an application entry associated with the authenticated user.
    3. If swipe right - Publishes the application ID to a Redis stream for asynchronous ML processing.

    Args:
        app_data (ApplicationCreate): Contains the job ID and swipe action.
        current_user (User): Authenticated user obtained via JWT.
        db (AsyncSession): Asynchronous SQLAlchemy database session.
        redis (RedisService): Redis service used to publish messages to the stream.

    Returns:
        ApplicationOut: Created application with full details.

    Raises:
        HTTPException: If application creation fails due to validation or server errors.
    """
    application_service = ApplicationService(db=db, redis=redis)

    try:
        # If user swipe right (apply for job)
        if app_data.swipe_action == SwipeAction.LIKE:
            application_right = await application_service.create_application(
                user_id=current_user.id,
                job_id=app_data.job_id,
                action=app_data.swipe_action
            )
            return application_right
        
        # If user swipe left (do not apply for job, keep track of this swipe)
        elif app_data.swipe_action == SwipeAction.DISLIKE:
            application_left = await application_service.record_swipe_history(
                user_id=current_user.id,
                job_id=app_data.job_id,
                action=app_data.swipe_action
            )
            return application_left
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create application"
        )

@router.patch("/{app_id}", response_model=ApplicationOut)
async def update_application(
    app_id: int,
    updates: ApplicationUpdate,
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the status or ML processing status of an existing application.

    Process:
    1. Accepts application ID and update fields (status, ml_status).
    2. Locates the application record in the database.
    3. Updates the relevant fields and saves changes.

    Args:
        app_id (int): ID of the application to update.
        updates (ApplicationUpdate): Fields to be updated (status and/or ml_status).
        db (AsyncSession): Asynchronous SQLAlchemy database session.
        current_user (User): Authenticated user obtained via JWT.

    Returns:
        ApplicationOut: Updated application data.

    Raises:
        HTTPException: If the application is not found or update fails.
    """
    application_service = ApplicationService(db=db, redis=None)  # Redis not needed here
    # Create a dict of non-None updates to pass to the service
    update_kwargs = {
        'app_id': app_id,
        'status': updates.status,
        'ml_status': updates.ml_status
    }
    
    # Filter out None values
    update_kwargs = {k: v for k, v in update_kwargs.items() if v is not None}
    
    return await application_service.update_application_status(**update_kwargs)

@router.get("/{app_id}", response_model=ApplicationOut)
async def get_application(
    app_id: int, 
    # db: Session = Depends(get_db),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve details of a specific application.

    Process:
    1. Accepts the application ID as input.
    2. Retrieves the corresponding record from the database.
    3. Returns full application details.

    Args:
        app_id (int): ID of the application to retrieve.
        db (AsyncSession): Asynchronous SQLAlchemy database session.
        current_user (User): Authenticated user obtained via JWT.

    Returns:
        ApplicationOut: Full application details.

    Raises:
        HTTPException: If the application is not found.
    """
    application_service = ApplicationService(db=db, redis=None)  # Redis not needed here
    return await application_service.get_application_status(
        app_id=app_id
    )

@router.get("/", response_model=List[ApplicationOut])
async def get_applications(
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(RedisService)
):
    """
    Fetch all applications for the currently logged-in user.

    Flow:
    1. Authenticates current user.
    2. Retrieves all applications where user is the target using cache (if available) or database.

    Args:
        db (AsyncSession): Active async database session.
        current_user (User): Current authenticated user object.

    Returns:
        List[ApplicationOut]: All applications for the current user.

    Raises:
        HTTPException: 401 if authentication fails.
    """
    application_service = ApplicationService(db=db, redis=redis)
    return await application_service.get_user_applications(requesting_user=current_user.id)

@router.patch("/{app_id}/withdraw", response_model=ApplicationOut)
async def withdraw_application(
    app_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
    redis: RedisService = Depends(RedisService)
):
    """
    Withdraw a job application (only for LIKE actions).
    
    Process:
    1. Verify the application belongs to the current user
    2. Check it's a LIKE action (can't withdraw dislikes)
    3. Update status to WITHDRAWN
    4. Notify ml service
    
    Returns:
        The withdrawn application
    
    Raises:
        403: If trying to withdraw someone else's application
        400: If trying to withdraw a DISLIKE action or application is already withdrawn or processed
        404: If application not found
        500: Other errors
    """
    application_service = ApplicationService(db=db, redis=redis)
    return await application_service.withdraw_application(
        app_id=app_id,
        user_id=current_user.id
    )