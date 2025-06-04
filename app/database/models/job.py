"""
SQLAlchemy Job Model
============================

Defines the database schema and ORM mapping for job listings.
This model represents the 'jobs' table in the database and
stores metadata related to job postings.

Includes:
- Job details and classifications
- Salary, location, and application info
- Full-text search support
- Indexes for optimized queries
"""

import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index, ARRAY, Text, Enum, Computed
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.database.models.enums.job import JobType, ExperienceLevel
from app.database.base import Base

class Job(Base):
    """
    Job posting entity representing an available job opportunity.

    Attributes:
        id (UUID): Primary key identifier (auto-generated UUID).
        title (str): Job title (e.g., 'Software Engineer').
        description (str): Full text description of the job.
        company_name (str): Company offering the job.
        contact_email (str): Contact email for applications or inquiries.
        location (str): Job location (e.g., 'Singapore').
        category (str): Job category or department (e.g., 'Engineering').
        remote_available (bool): Whether remote work is allowed.
        salary_min (int): Minimum salary offered.
        salary_max (int): Maximum salary offered.
        currency (str): Currency for salary (default: 'SGD').
        job_type (JobType): Type of job (e.g., full-time, part-time).
        experience_level (ExperienceLevel): Required experience level.
        skills_required (List[str]): List of required technical or soft skills.
        language (List[str]): Languages required for the role.
        is_active (bool): Whether the job listing is currently active.
        apply_url (str): External URL for job application (if any).
        posted_at (datetime): Timestamp when the job was posted.
        expires_at (datetime): When the listing expires (default: 30 days).
        search_vector (TSVECTOR): Auto-generated full-text search field.
    """
    __tablename__ = "jobs"
    
    # Primary and basic details
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(Integer, nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    company_name = Column(String(100))
    contact_email = Column(String(100))
    location = Column(String(100))
    category = Column(String(50))
    remote_available = Column(Boolean, default=False)

    # Compensation
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    currency = Column(String(3), default="SGD")

    # Job classification
    job_type = Column(Enum(JobType))
    experience_level = Column(Enum(ExperienceLevel))

    # Additional metadata
    skills_required = Column(ARRAY(String))
    language = Column(ARRAY(String))
    is_active = Column(Boolean, default=True)
    apply_url = Column(String(300))

    # Time metadata
    posted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, server_default=func.now() + timedelta(days=30))
    
    # Corrected full-text search implementation
    search_vector = Column(
        TSVECTOR(),
        Computed("to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))"),
        # Remove the persisted=True parameter
    )

    # Report tracking (preserved even if job is deleted)
    report_count = Column(Integer, default=0, server_default='0')
    reports = relationship("JobReport", back_populates="job")

    # Indexes for query performance
    __table_args__ = (
        # Partial index for active jobs
        Index('idx_active_jobs', 'is_active', postgresql_where=(is_active == True)),
        
        # Composite index for common search patterns
        Index('idx_job_search', 'location', 'remote_available', 'job_type', 
              postgresql_where=(is_active == True)),
              
        # Index for salary ranges
        Index('idx_salary_range', 'salary_min', 'salary_max'),
        
        # GIN index for search vector
        Index('idx_search_vector', 'search_vector', postgresql_using='gin')
    )

    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company_name}')>"