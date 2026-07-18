from enum import StrEnum


class WorkbenchStage(StrEnum):
    SUBMITTED = "submitted"
    VALIDATION = "validation"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
