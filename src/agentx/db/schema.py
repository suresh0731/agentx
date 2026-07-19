from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InstructionRow(Base):
    __tablename__ = "instructions"

    instruction_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    filename: Mapped[str | None] = mapped_column(String(256))
    intent: Mapped[str | None] = mapped_column(String(32))
    channel: Mapped[str | None] = mapped_column(String(64))
    routing_target: Mapped[str | None] = mapped_column(String(8))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(64), default="Processing")
    status_tone: Mapped[str | None] = mapped_column(String(16))
    journey: Mapped[dict] = mapped_column(JSON, default=dict)
    meta: Mapped[str | None] = mapped_column(String(256))
    stage_label: Mapped[str | None] = mapped_column(String(128))
    recon_status: Mapped[str | None] = mapped_column(String(32))
    recon_detail: Mapped[str | None] = mapped_column(Text)
    golden_schema: Mapped[dict | None] = mapped_column(JSON)
    intake_json: Mapped[dict | None] = mapped_column(JSON)
    party: Mapped[str | None] = mapped_column(String(128))
    account: Mapped[str | None] = mapped_column(String(128))
    settlement_date: Mapped[str | None] = mapped_column(String(32))
    settlement_display: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[float | None] = mapped_column(Float)
    amount_display: Mapped[str | None] = mapped_column(String(64))
    quantity: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(8))
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    repair_notes: Mapped[list] = mapped_column(JSON, default=list)
    field_confidences: Mapped[dict] = mapped_column(JSON, default=dict)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    is_exception: Mapped[bool] = mapped_column(default=False)
    exception: Mapped[dict | None] = mapped_column(JSON)
    in_queue: Mapped[bool] = mapped_column(default=True)
    workbench_request_id: Mapped[str | None] = mapped_column(String(32))
    source_type: Mapped[str | None] = mapped_column(String(32))
    workbench_stage: Mapped[str | None] = mapped_column(String(32))


class WorkbenchRequestRow(Base):
    __tablename__ = "workbench_requests"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    ref: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(32))
    intent: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(64))
    party: Mapped[str] = mapped_column(String(128))
    amount: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    risk: Mapped[int] = mapped_column(Integer, default=0)
    risk_label: Mapped[str] = mapped_column(String(16), default="Low")
    sla_minutes: Mapped[int] = mapped_column(Integer, default=60)
    sla_remaining: Mapped[int] = mapped_column(Integer, default=60)
    assignee: Mapped[str] = mapped_column(String(64), default="—")
    path: Mapped[str] = mapped_column(String(32), default="new")
    journey: Mapped[dict] = mapped_column(JSON, default=dict)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    explain: Mapped[str] = mapped_column(Text, default="")
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    comments: Mapped[list] = mapped_column(JSON, default=list)


class EvidenceEventRow(Base):
    __tablename__ = "evidence_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    instruction_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    stage: Mapped[int] = mapped_column(Integer)
    stage_label: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(64))


class MetricRollupRow(Base):
    __tablename__ = "metric_rollups"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ConfigRuleRow(Base):
    __tablename__ = "config_rules"

    category: Mapped[str] = mapped_column(String(32), primary_key=True)
    rules: Mapped[list] = mapped_column(JSON)


class PipelineRunRow(Base):
    __tablename__ = "pipeline_runs"

    instruction_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="running")
    checkpoint: Mapped[dict | None] = mapped_column(JSON)
