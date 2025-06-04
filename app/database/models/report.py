"""
SQLAlchemy Job report Model
============================

Defines the database schema and ORM mapping for job reports.
This model represents the 'job_reports' table in the database and
stores metadata related to job reports postings.

Includes:
- Job details
- Reporter details
- Report details
- Status of report
- Reviewer information
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database.base import Base
from app.database.models.enums.report import ReportStatus

class JobReport(Base):
    """
    Job report entity representing the reporting imformation.

    Attributes:
        id (int): Primary key identifier (auto-generated int).
        job_id (UUID): Job id linked to jobs table.
        reporter_id (int): User id of the reporter linked to user table.
        reviewed_by (int): User id of the reviewer linked to user table.
        reason (str): Reason for reporting.
        reported_at (DateTime): Time of reporting.
        status (Enum(ReportStatus)): Status of the report (e.g. pending).
    """
    __tablename__ = "job_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(UUID, ForeignKey("jobs.id", ondelete="RESTRICT"), index=True, nullable=False)
    reporter_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)

    reason = Column(String(500), nullable=False)
    reported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="reports")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reported_jobs")
    reviewer = relationship("User", foreign_keys=[reviewed_by], back_populates="reviewed_reports")

    def __repr__(self):
            return f"<Job report(id={self.id}, job_id='{self.job_id}', reporter_id='{self.reporter_id}')>"