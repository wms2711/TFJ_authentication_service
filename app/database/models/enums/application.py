"""
Application Model Enums
=========================

Defines enumerations used for tracking statuses across different application processes:
1. Database model representations

Includes:
- Job application lifecycle statuses
- Machine learning task statuses
"""
from enum import Enum

class ApplicationStatus(str, Enum):
    """
    Represents the lifecycle status of a job application.

    Values:
        PENDING: Application has been submitted but not yet processed.
        PROCESSING: Application is currently being reviewed or assessed.
        COMPLETED: Application process has been successfully completed (e.g., hired).
        FAILED: Application encountered an error and could not be processed.
        REJECTED: Application was reviewed and not selected by the employer.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"  # Optional: If employers can reject

class MLTaskStatus(str, Enum):
    """
    Represents the status of ML service processing the application task.

    Values:
        QUEUED: Task is waiting in the queue to be processed.
        RUNNING: Task is currently being executed.
        SUCCESS: Task completed successfully.
        FAILED: Task failed due to an error.
    """
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"