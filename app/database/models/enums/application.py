from enum import Enum

class ApplicationStatus(str, Enum):
    """Tracks lifecycle of a job application"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"  # Optional: If employers can reject

class MLTaskStatus(str, Enum):
    """Tracks ML service state"""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"