"""
Job Management Service
=======================

Handles business logic for job posting operations:
- Job creation
- Job updates
- Job retrieval
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.job import Job
from app.schemas.job import JobCreate, JobInDB
from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime, timedelta
import logging
import uuid

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class JobService:
    """Service handling job posting operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize service with database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session
        """
        self.db = db

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