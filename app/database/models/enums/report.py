"""
Job report Model Enums
=========================

Defines the database model structure for the statuses column:
1. Database model representations

Includes:
- Job report status
"""

from enum import Enum

class ReportStatus(str, Enum):
    """
    Represents the status of reporting jpbs.

    Values:
        PENDING: Pending review from job poster / admins.
        REVIEWED: Reviewed by job poster / admins.
        DISMISSED: Dismissed report.
        ACTIONED: Took actions.
    """
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"