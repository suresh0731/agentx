from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class FieldValidation(BaseModel):
    field: str
    ingested_value: str
    external_value: str
    status: str = "matched"


class ValidationCounts(BaseModel):
    total: int
    matched: int
    mismatched: int


class ReconcileValidateRequest(BaseModel):
    instruction_id: str
    destination: str
    ingested_record: dict[str, Any] = Field(default_factory=dict)
    route_reference: str | None = None


class ReconcileValidateResponse(BaseModel):
    status: str = "matched"
    matched: bool = True
    summary: str
    agent_output: str
    external_reference: str
    validated_at: str
    destination: str
    field_validations: list[FieldValidation] = Field(default_factory=list)
    counts: ValidationCounts
