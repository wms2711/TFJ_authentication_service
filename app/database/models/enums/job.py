"""
Job Model Enums
=========================

Defines the database model structure for the statuses column:
1. Database model representations

Includes:
- Job types
- Experience level
"""
from enum import Enum

class JobType(str, Enum):
    """
    Represents the type of job offered.

    Values:
        FULL_TIME: Standard full-time employment.
        PART_TIME: Work schedule less than full-time.
        CONTRACT: Fixed-term employment.
        INTERNSHIP: Training role, typically for students or recent graduates.
        TEMPORARY: Short-term employment, may be seasonal or project-based.
    """
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"

class ExperienceLevel(str, Enum):
    """
    Represents the required or expected experience level for a job.

    Values:
        ENTRY: For candidates new to the workforce or specific field.
        MID: Mid-level roles requiring some experience.
        SENIOR: Senior-level positions with significant experience and responsibility.
        LEAD: Leadership roles often involving managing teams or projects.
        EXECUTIVE: High-level strategic roles (e.g., director, VP).
    """
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"