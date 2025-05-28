from fastapi import APIRouter, Depends, HTTPException, Query,status
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.job import JobCreate, JobUpdate, JobInDB, JobSearchResult
from app.services.job import JobService
from app.services.redis import RedisService
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
            detail="Only employers or admins can post jobs"
        )
    job_service = JobService(db=db, redis_service=None)
    return await job_service.create_job(job_data, creator_id=current_user.id)

@router.patch("/{job_id}", response_model=JobInDB)
async def update_job(
    job_id: UUID,
    job_data: JobUpdate,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify user has permission to update jobs (only employer or admin)
    if not current_user.is_employer and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employers or admins can update jobs"
        )
    job_service = JobService(db=db, redis_service=None)
    return await job_service.update_job(
        job_id=job_id,
        update_data=job_data,
        updater_id=current_user.id
    )

@router.get("/{job_id}", response_model=JobInDB)
async def get_specific_job(
    job_id: UUID,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    job_service = JobService(db=db, redis_service=None)
    return await job_service.get_specific_job(
        job_id=job_id,
        current_user=current_user
    )

@router.get("/", response_model=JobSearchResult)
async def search_jobs(
    location: Optional[str] = Query(None),
    remote: Optional[bool] = Query(None),
    title: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    job_type: Optional[JobType] = Query(None),
    experience: Optional[ExperienceLevel] = Query(None),
    skills: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
    redis: RedisService = Depends(RedisService)
):
    """
    Search jobs with caching and pagination
    
    Returns:
        - Active, non-expired jobs for regular users
        - All jobs for admins/creators
        - Cached results when available
    """
    job_service = JobService(db=db, redis_service=redis)
    return await job_service.search_jobs(
        location=location,
        remote=remote,
        title=title,
        salary_min=salary_min,
        job_type=job_type,
        experience=experience,
        skills=skills,
        page=page,
        page_size=page_size,
        current_user=current_user
    )