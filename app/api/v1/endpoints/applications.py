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
    application_service = ApplicationService(db=db, redis=None)  # Redis not needed here
    return application_service.update_application_status(
        app_id=app_id,
        status=updates.status,
        ml_status=updates.ml_status
    )