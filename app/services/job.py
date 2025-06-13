"""
Job Management Service
=======================

Handles business logic for job posting operations:
- Job creation
- Job updates
- Job retrieval
"""

from sqlalchemy import select, and_
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.job import Job
from app.database.models.application import Application
from app.database.models.report import JobReport
from app.schemas.job import JobCreate, JobInDB, JobUpdate, JobSearchResult, JobReportInDb
from app.database.models.enums.job import JobType, ExperienceLevel
from app.database.models.enums.report import ReportStatus
from app.services.redis import RedisService
from app.services.email import EmailService
from fastapi import HTTPException, status, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timedelta
from utils.logger import init_logger
from uuid import UUID
from app.database.models.user import User
from app.config import settings

# Configure logger
logger = init_logger("JobService")

class JobService:
    """Service handling job posting operations."""

    def __init__(
            self, 
            db: AsyncSession, 
            redis_service: Optional[RedisService] = None,
            email_service: Optional[EmailService] = None
        ):
        """
        Initialize service with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session
        """
        self.db = db
        self.redis = redis_service
        self.email = email_service

    async def create_job(
        self, 
        job_data: JobCreate, 
        creator_id: int
    ) -> JobInDB:
        """
        Create a new job posting.
        
        Flow:
        1. Validates input data
        2. Creates new Job DB record
        3. Commits to database
        4. Returns the created job
        
        Args:
            job_data (JobCreate): Validated job creation data
            creator_id (int): ID of the user creating the job
            
        Returns:
            JobInDB: Serialized job details
            
        Raises:
            ValueError: For invalid inputs or database operations
            HTTPException: Should be raised by the router for HTTP status codes
        """
        try:
            # Validate creator_id
            if not isinstance(creator_id, int) or creator_id < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid creator ID"
                )
            
            # Create job with additional system fields
            job = Job(
                **job_data.dict(),
                creator_id=creator_id,
                is_active=True,
                posted_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30)  # Default 30-day expiration
            )

            self.db.add(job)
            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(job)

            if not job.id:
                raise ValueError("Failed to retrieve job ID after insert")
            return JobInDB.model_validate(job)
        
        except HTTPException:
            raise
        except Exception as e:
        # Automatic rollback occurs on exception
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create job: {str(e)}"
            )
        
    async def update_job(
        self,
        job_id: UUID,
        update_data: JobUpdate,
        updater_id: int
        ) -> JobInDB:
        """
        Update an existing job posting.
        
        Args:
            job_id: UUID of the job to update
            update_data: Validated job update data
            updater_id: ID of the user making the update
            
        Returns:
            JobInDB: Updated job details
            
        Raises:
            HTTPException: Appropriate status codes for different failure scenarios
        """
        try:
            # Get the existing job
            result = await self.db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalars().first()
            if not job:
                logger.error(f"Job not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            if job.creator_id != updater_id:
                logger.error(f"Only job creator can edit this job")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Only job creator can edit this job"
                )
            
            # Extract only provided fields to update
            data_to_update = update_data.dict(exclude_unset=True)

            # Update job information
            for field, value in data_to_update.items():
                setattr(job, field, value)
            job.creator_id = updater_id

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Database commit failed for job id={job_id}: {db_exc}")
                raise ValueError(f"Database commit failed: {str(db_exc)}")
            await self.db.refresh(job)
            return JobInDB.model_validate(job)
        
        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Unexpected error during user job for job id={job_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update job"
            )
        
    async def get_specific_job(
        self,
        job_id: UUID,
        current_user: User
    ) -> JobInDB:
        """
        Retrieve a specific job with expiration and permission checks.
        
        Args:
            job_id: UUID of the job to retrieve
            current_user: Authenticated user making the request
            
        Returns:
            JobInDB: The requested job details
            
        Raises:
            HTTPException: 404 if job not found
            HTTPException: 403 if user cannot view expired/inactive job
        """
        try:
            # Get job from database
            result = await self.db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalars().first()
            if not job:
                logger.error(f"Job not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            # See of job is expired (only admin and job creator can get job post if expired)
            current_time = datetime.utcnow()
            is_expired = job.expires_at < current_time
            is_creator = job.creator_id == current_user.id

            if is_expired and not (current_user.is_admin or is_creator):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Expired jobs can only be viewed by admins or the job creator"
                )
            if not job.is_active and not (current_user.is_admin or is_creator):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Inactive jobs can only be viewed by admins or the job creator"
                )
            return JobInDB.model_validate(job)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve job"
            )
    
    async def search_jobs(
        self,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        title: Optional[str] = None,
        salary_min: Optional[int] = None,
        job_type: Optional[JobType] = None,
        experience: Optional[ExperienceLevel] = None,
        skills: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        current_user: Optional[User] = None
    ) -> JobSearchResult:
        """
        Search for jobs with caching and filtering support.

        Args:
            location (str, optional): Filter by job location (partial match)
            remote (bool, optional): Filter by remote availability
            title (str, optional): Filter by job title (partial match)
            salary_min (int, optional): Minimum acceptable salary
            job_type (JobType, optional): Job type enum (FULL_TIME, PART_TIME, etc.)
            experience (ExperienceLevel, optional): Experience level enum (JUNIOR, MID, etc.)
            skills (List[str], optional): List of required skills (must all be present)
            page (int): Page number (default: 1)
            page_size (int): Results per page (default: 20)
            current_user (User, optional): Authenticated user object

        Returns:
            JobSearchResult: A paginated and optionally cached list of matching jobs, 
            along with metadata including total results and total pages.

        Raises:
            HTTPException: 500 Internal Server Error if search or database access fails
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                "jobs:search",
                location=location,
                remote=remote,
                title=title,
                salary_min=salary_min,
                job_type=job_type,
                experience=experience,
                skills=skills,
                page=page,
                page_size=page_size,
                is_admin=getattr(current_user, "is_admin", False),
                user_id=getattr(current_user, "id", None)
            )

            try:
            # Try cache first
                if cached := await self.redis.get_cache(cache_key):
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return JobSearchResult.model_validate_json(cached)
            except Exception as e:
                logger.warning(f"Cache check failed, proceeding to DB: {str(e)}")
            
            # Database query
            query = select(Job)
            filters = []
            
            # Add filters (maintain order for query planning)
            if location:
                filters.append(Job.location.ilike(f"%{location}%"))
            if remote is not None:
                filters.append(Job.remote_available == remote)
            if title:
                filters.append(Job.title.ilike(f"%{title}%")) 
            if salary_min:
                filters.append(Job.salary_max >= salary_min)
            if job_type:
                filters.append(Job.job_type == job_type)
            if experience:
                filters.append(Job.experience_level == experience)
            if skills:
                filters.append(Job.skills_required.contains(skills))
        
            # Apply all filters at once
            if filters:
                query = query.where(and_(*filters))

            # If user is not admin, shows only active and non-expired jobs
            if not getattr(current_user, "is_admin", False):
                query = query.where(
                    Job.is_active == True,
                    Job.expires_at >= datetime.utcnow()
                )

            # Exclude jobs that user already swiped
            if current_user and current_user.id:
                swiped_jobs = select(Application.job_id).where(
                    Application.user_id == current_user.id
                )
                # Use the select() directly in not_in()
                query = query.where(
                    Job.id.not_in(swiped_jobs)
                )

            # Get total count 
            total = await self.db.scalar(
                query.with_only_columns(func.count(Job.id))
            )

            # Apply pagination
            results = await self.db.scalars(
                query.offset((page - 1) * page_size)
                .limit(page_size)
            )

            # Prepare response
            response = JobSearchResult(
                results=[JobInDB.model_validate(job) for job in results],
                meta={
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            )

            # Cache the results (async fire-and-forget)
            try:
                await self.redis.set_cache(
                    cache_key, 
                    response.model_dump_json(),
                    ttl=300   # 5 mins
                    )
            except Exception as e:
                logger.error(f"Cache set failed: {str(e)}")
                # Don't fail the request if caching fails
            return response
        
        except Exception as e:
            logger.exception(f"Job search failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Job search failed"
            )

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a unique Redis cache key based on input parameters.

        Used in:
        - Caching job search queries

        Example:
        >>> _generate_cache_key("jobs:search", location="NY", title="Engineer", page=1)
        'jobs:search:location=NY|page=1|title=Engineer'

        Args:
            prefix (str): Cache namespace prefix (e.g., "jobs:search")
            **kwargs: Arbitrary filter parameters

        Returns:
            str: A cache key suitable for Redis
        """
        params = []
        for k, v in sorted(kwargs.items()):
            if v is not None:
                if isinstance(v, list):
                    params.append(f"{k}={','.join(sorted(v))}")
                else:
                    params.append(f"{k}={v}")
        return f"{prefix}:{'|'.join(params)}"

    async def report_job(
        self,
        job_id: UUID,
        reporter_id: int,
        reason: str,
        current_user: User,
        background_tasks: BackgroundTasks
    )-> JobReportInDb:
        """
        Report a job posting for review by admins.

        Flow:
        1. Verify job exists
        2. Check if user has already reported this job
        3. Create report record
        4. Optionally trigger notifications to admins

        Args:
            job_id: UUID of the job being reported
            reporter_id: ID of the user making the report
            reason: Detailed reason for the report

        Raises:
            HTTPException: With appropriate status codes for various failure scenarios
        """
        try:
            # Verify job exists
            result = await self.db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalars().first()
            if not job:
                logger.error(f"Job not found for reporting: {job_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job not found"
                )
            
            # Check if user already reported
            existing_report = await self.db.execute(
                select(JobReport)
                .where(
                    and_(
                        JobReport.job_id == job_id,
                        JobReport.reporter_id == reporter_id
                    )
                )
            )
            existing_report_result = existing_report.scalars().first()
            if existing_report_result:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already reported this job"
                )
            
            # Create new report
            report = JobReport(
                job_id=job_id,
                reporter_id=reporter_id,
                reason=reason,
                reported_at=datetime.utcnow(),
                status=ReportStatus.PENDING
            )
            self.db.add(report)

            # Increment report count for job
            job.report_count = (job.report_count or 0) + 1

            try:
                await self.db.commit()
            except Exception as db_exc:
                await self.db.rollback()
                logger.error(f"Failed to create job report: {str(db_exc)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process job report"
                )
            
            
            # Verify job creator exists and is employer/admin
            creator = await self.db.execute(
                select(User).where(User.id == job.creator_id)
            )
            creator_result = creator.scalars().first()

            # Prepare notification details
            notification_title = f"New report for job: {job.title}"
            notification_message = (
                f"Job ID: {job_id}\n"
                f"Report Reason: {reason}\n"
                f"Reported By: {current_user.full_name or current_user.username}\n"
                f"Reported At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            )

            # Send email notification to employer/admin creators
            if self.email:
                if creator_result and (creator_result.is_employer or creator_result.is_admin):
                    background_tasks.add_task(
                        self.email.send_email_notification,
                        creator_result.email,
                        notification_title,
                        notification_message
                    )
                else:
                    background_tasks.add_task(
                        self.email.send_email_notification,
                        settings.ADMIN_SENDER_EMAIL,
                        notification_title,
                        notification_message
                    )
            
            await self.db.refresh(report)
            return JobReportInDb.model_validate(report)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during job reporting: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process job report"
            )