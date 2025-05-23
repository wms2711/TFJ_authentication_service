import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index, ARRAY, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from app.database.models.enums.job import JobType, ExperienceLevel
from app.database.base import Base

class Job(Base):
    __tablename__ = "jobs"
    
    # Job information
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    company_name = Column(String(100))
    contact_email = Column(String(100))
    location = Column(String(100))
    category = Column(String(50))
    remote_available = Column(Boolean, default=False)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    currency = Column(String(3), default="SGD")
    job_type = Column(Enum(JobType))
    experience_level = Column(Enum(ExperienceLevel))
    skills_required = Column(ARRAY(String))
    language = Column(ARRAY(String))
    is_active = Column(Boolean, default=True)
    apply_url = Column(String(300))  # For external applications

    # Post time and expiry (default 30 days)
    posted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, server_default=func.now() + timedelta(days=30))
    
    # For full-text search
    search_vector = Column(
        TSVECTOR(), 
        computed="to_tsvector('english', title || ' ' || description)", 
        persisted=True
        )

    __table_args__ = (
        # Partial index for active jobs
        Index('idx_active_jobs', 'is_active', postgresql_where=(is_active == True)),
        
        # Composite index for common search patterns
        Index('idx_job_search', 'location', 'remote_available', 'job_type', 
              postgresql_where=(is_active == True)),
              
        # Index for salary ranges
        Index('idx_salary_range', 'salary_min', 'salary_max'),
    )