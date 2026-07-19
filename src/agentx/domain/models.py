from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JourneyState(BaseModel):
    state: str | None = None
    completed_through: int = 0
    active_step: int | None = None
    held_step: int | None = None
    failed_step: int | None = None


class InstructionState(BaseModel):
    instruction_id: str
    channel: str = ""
    source_type: str = ""
    intake_json: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None
    destination: str | None = None
    golden_schema: dict[str, Any] = Field(default_factory=dict)
    field_confidences: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    journey: JourneyState = Field(default_factory=JourneyState)
    workbench_stage: str = "submitted"
    status: str = "Processing"
    findings: list[str] = Field(default_factory=list)
    explainability: str = ""
    decisions: list[str] = Field(default_factory=list)
    repair_notes: list[str] = Field(default_factory=list)
    error: str | None = None
    failed_step: int | None = None
    needs_human_review: bool = False
    thread_id: str | None = None
    timeline: list[str] = Field(default_factory=list)
    risk_score: int = 0
    risk_label: str = "Low"
