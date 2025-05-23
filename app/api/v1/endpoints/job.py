from fastapi import APIRouter, Depends, HTTPException, Query,status
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.job import JobCreate, JobUpdate, JobInDB, JobSearchResult
from app.services.job import JobService
from app.database.models.enums.job import JobType, ExperienceLevel
from app.database.session import get_db, async_get_db
from app.database.models.user import User
from app.dependencies import get_current_user

# Initialize router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/job",
    tags=["job"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=JobInDB)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
    ):

    # Verify user has permission to post jobs (only employer or admin)
    if not current_user.is_employer and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers can post jobs"
        )
    job_service = JobService(db)
    return await job_service.create_job(job_data)