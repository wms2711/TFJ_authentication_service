"""
Application Management Router
=============================

Handles job application-related operations including:
- Submitting new job applications to redis pub-sub
- Updating application or ML processing status
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.services.application import ApplicationService
from app.services.redis import RedisService
from app.dependencies import get_current_user
from app.database.models.user import User
from app.database.session import get_db

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/application",
    tags=["application"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ApplicationOut)
def create_application(
    app_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: RedisService = Depends(RedisService)
):
    """
    Create a new job application

    Flow:
    1. Receives job_id in request body
    2. Creates an application record tied to the current user
    3. Publishes the application ID to Redis stream for ML processing

    Args:
        app_data: Job ID payload (from ApplicationCreate schema)
        current_user: Authenticated user from JWT
        db: Active SQLAlchemy session
        redis: Redis service for publishing to stream

    Returns:
        ApplicationOut: Full application details after creation

    Raises:
        HTTPException: On any database or Redis failure
    """
    application_service = ApplicationService(db=db, redis=redis)
    return application_service.create_application(
        user_id=current_user.id,
        job_id=app_data.job_id
    )

@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(
    app_id: int,
    updates: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the status or ML status of an existing application

    Flow:
    1. Accepts optional status or ml_status fields
    2. Finds the application by ID
    3. Updates relevant fields and saves to DB

    Args:
        app_id: ID of the application to update
        updates: Fields to update (status, ml_status)
        db: Active SQLAlchemy session
        current_user: Authenticated user from JWT

    Returns:
        ApplicationOut: Updated application details

    Raises:
        HTTPException: 404 if application not found
    """
    application_service = ApplicationService(db=db, redis=None)  # Redis not needed here
    return application_service.update_application_status(
        app_id=app_id,
        status=updates.status,
        ml_status=updates.ml_status
    )