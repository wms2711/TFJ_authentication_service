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
        NA: No application was made because user swiped left.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"  # Optional: If employers can reject
    NA = "NA"  # If user swipe left, no application was made
    WITHDRAWN = "withdrawn"  # User withdraw their application

class MLTaskStatus(str, Enum):
    """
    Represents the status of ML service processing the application task.

    Values:
        QUEUED: Task is waiting in the queue to be processed.
        RUNNING: Task is currently being executed.
        SUCCESS: Task completed successfully.
        FAILED: Task failed due to an error.
        NA: No application was made because user swiped left.
    """
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NA = "NA"  # If user swipe left, no application was made

class SwipeAction(str, Enum):
    """
    Represents user swipe left (dislike) or swipe right (like).

    Values:
        LIKE: Swipe right - creates application.
        DISLIKE: swipe left - track in history.
        SUCCESS: Task completed successfully.
        FAILED: Task failed due to an error.
    """
    LIKE = "like"
    DISLIKE = "dislike"

class RedisAction(str, Enum):
    """
    Represents user action for posting to redis.

    Values:
        APPLY: applying for job, send to redis for ml service.
        WITHDRAW: withdrawing from the application, send to redis for ml service.
    """
    APPLY = "apply"
    WITHDRAW = "withdraw"