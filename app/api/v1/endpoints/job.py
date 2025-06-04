"""
Job Router
==========

Handles all job-related operations including:
- Creating jobs (restricted to employers/admins)
- Updating jobs (restricted to employers/admins and job creator)
- Viewing specific job postings
- Searching for jobs (with filters, pagination, and Redis caching)
"""

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
    """
    Create a new job posting.

    Access:
    - Only accessible by employers or admins.

    Args:
        job_data (JobCreate): Data required to create a new job.
        db (AsyncSession): Database session.
        current_user (User): Authenticated user.

    Returns:
        JobInDB: Created job record.

    Raises:
        HTTPException: 403 if user is not authorized.
    """
    # Verify user has permission to create jobs (only employer or admin)
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
    """
    Update an existing job posting.

    Access:
    - Only accessible by employers or admins.

    Args:
        job_id (UUID): Job identifier.
        job_data (JobUpdate): Fields to update.
        db (AsyncSession): Database session.
        current_user (User): Authenticated user.

    Returns:
        JobInDB: Updated job record.

    Raises:
        HTTPException: 403 if unauthorized.
    """
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
    """
    Get a specific job by ID.

    Args:
        job_id (UUID): Job identifier.
        db (AsyncSession): Database session.
        current_user (User): Authenticated user.

    Returns:
        JobInDB: Job details.

    Raises:
        HTTPException: 404 if job not found.
    """
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
    Search job listings using filters, pagination, and caching.

    Access:
    - Regular users see only active jobs.
    - Admins and creators see all jobs.

    Filters:
    - Location
    - Remote (bool)
    - Title (fuzzy search)
    - Minimum salary
    - Job type (Full-time, Part-time, etc.)
    - Experience level
    - Skills (list)

    Pagination:
    - Default: page=1, page_size=20

    Caching:
    - Redis used to cache repeated queries for performance.

    Args:
        location (str): Job location.
        remote (bool): Remote jobs only.
        title (str): Job title.
        salary_min (int): Minimum salary.
        job_type (JobType): Enum of job types.
        experience (ExperienceLevel): Enum of experience levels.
        skills (List[str]): Required skills.
        page (int): Page number.
        page_size (int): Results per page.
        db (AsyncSession): Database session.
        current_user (User): Authenticated user.
        redis (RedisService): Redis service instance.

    Returns:
        JobSearchResult: List of matched jobs and pagination metadata.
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

@router.post("/{job_id}/report", status_code=status.HTTP_200_OK)
async def report_job(
    job_id: UUID,
    reason: str = Query(..., min_length=10, max_length=500, description="Reason for reporting the job"),
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Report a job posting for inappropriate content or violations.

    Access:
    - All authenticated users can report jobs.

    Args:
        job_id: UUID of the job to report
        reason: Detailed reason for the report
        db: Database session
        current_user: Authenticated user making the report

    Returns:
        dict: Success message

    Raises:
        HTTPException: If job not found or other errors occur
    """
    job_service = JobService(db=db, redis_service=None)
    await job_service.report_job(
        job_id=job_id,
        reporter_id=current_user.id,
        reason=reason
    )
    return {"message": "Job reported successfully. Our team will review it shortly."}