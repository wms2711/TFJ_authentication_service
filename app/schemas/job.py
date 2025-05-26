"""
Jobs Data Schemas
=========================

Defines the data structures for jobs:
1. API request/response formats
2. Internal service transfers

Includes:
- Job details base model (job title, job despcription, company name)
- Schema for job creation
- Schema for job update
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, UUID4
from app.database.models.enums.job import JobType, ExperienceLevel

class JobBase(BaseModel):
    """
    Base model for job details.

    Fields:
        title (str): Job title (mandatory).
        description (Optional[str]): Job description.
        company_name (Optional[str]): Company name offering the job.
        contact_email (Optional[str]): Email for job contact.
        location (Optional[str]): Job location.
        category (Optional[str]): Job category or industry.
        remote_available (bool): Whether remote work is possible (default: False).
        salary_min (Optional[int]): Minimum salary offered.
        salary_max (Optional[int]): Maximum salary offered.
        currency (str): Currency for salary, default is "SGD".
        job_type (Optional[JobType]): Type of job (e.g., full-time, part-time).
        experience_level (Optional[ExperienceLevel]): Required experience level.
        skills_required (List[str]): List of required skills.
        language (List[str]): List of preferred or required languages.
        apply_url (Optional[str]): URL to apply for the job.
    """
    title: str
    description: Optional[str] = None
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    remote_available: bool = False
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "SGD"
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    skills_required: List[str] = []
    language: List[str] = []
    apply_url: Optional[str] = None

class JobCreate(JobBase):
    """
    Schema for creating a job.

    Inherits all fields from JobBase.
    """
    pass

class JobUpdate(BaseModel):
    """
    Schema for updating a job post.

    All fields are optional to allow partial updates.

    Fields:
        title (Optional[str]): Updated job title.
        description (Optional[str]): Updated job description.
        company_name (Optional[str]): Updated company name.
        contact_email (Optional[str]): Updated contact email.
        location (Optional[str]): Updated location.
        category (Optional[str]): Updated job category.
        remote_available (Optional[bool]): Updated remote work availability.
        salary_min (Optional[int]): Updated minimum salary.
        salary_max (Optional[int]): Updated maximum salary.
        currency (Optional[str]): Updated currency.
        job_type (Optional[JobType]): Updated job type.
        experience_level (Optional[ExperienceLevel]): Updated experience level.
        skills_required (Optional[List[str]]): Updated list of skills.
        language (Optional[List[str]]): Updated list of languages.
        apply_url (Optional[str]): Updated application URL.
        is_active (Optional[bool]): Updated job active status.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    remote_available: Optional[bool] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    job_type: Optional[JobType] = None
    experience_level: Optional[ExperienceLevel] = None
    skills_required: Optional[List[str]] = None
    language: Optional[List[str]] = None
    apply_url: Optional[str] = None
    is_active: Optional[bool] = None
    
    class Config:
        extra = "forbid"  # Prevent unknown fields
        json_encoders = {
            JobType: lambda v: v.value if v else None,
            ExperienceLevel: lambda v: v.value if v else None
        }

class JobInDB(JobBase):
    """
    Full job model for data persistence layer.

    Fields:
        id (UUID4): Unique job identifier.
        is_active (bool): Job's active status.
        posted_at (datetime): Job posting timestamp.
        expires_at (datetime): Expiry date for the job post.

    Config:
        from_attributes: Enables ORM mode for SQLAlchemy compatibility.
    """
    id: UUID4
    is_active: bool
    posted_at: datetime
    expires_at: datetime
    
    class Config:
        from_attributes = True

class JobSearchResult(BaseModel):
    """
    Schema for search results of job listings.

    Fields:
        meta (dict): Metadata like pagination, total count, etc.
        results (List[JobInDB]): List of job entries matching the search criteria.
    """
    meta: dict
    results: List[JobInDB]