from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.database.base import Base
from app.database.models.enums.report import ReportStatus

class JobReport(Base):
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
