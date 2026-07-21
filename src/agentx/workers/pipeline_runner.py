import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agentx.api.serializers import exception_summary, instruction_summary, workbench_card
from agentx.config import settings
from agentx.db.repositories.instruction_repo import InstructionRepository, WorkbenchRepository
from agentx.db.schema import InstructionRow, WorkbenchRequestRow
from agentx.layers.ingest.idp_schema import (
    append_timeline,
    format_amount_display,
    format_source_label,
    normalize_source_label,
    normalize_source_type,
    parse_extraction_fields,
    round_confidence,
)
from agentx.layers.orchestrator.graph import reconcile_node, route_node

logger = logging.getLogger(__name__)

BroadcastFn = Callable[[dict], Awaitable[None]]


def _journey_dict(inst: dict) -> dict:
    journey = inst.get("journey") or {}
    if hasattr(journey, "model_dump"):
        return journey.model_dump()
    return dict(journey)


def _investor_name(inst: dict) -> str:
    golden = inst.get("golden_schema") or {}
    intake = inst.get("intake_json") or {}
    extraction = intake.get("extraction_result") or {}
    values, _ = parse_extraction_fields(extraction) if extraction else ({}, {})
    transaction = intake.get("transaction") or {}
    return (
        golden.get("investor_account_name")
        or values.get("investor_account_name")
        or intake.get("party", {}).get("name")
        or transaction.get("investor_account_name")
        or "Unknown"
    )


def _build_exception(inst: dict) -> dict | None:
    if not inst.get("needs_human_review"):
        return None

    journey = _journey_dict(inst)
    failed_step = journey.get("failed_step") or journey.get("failedStep")
    held_step = journey.get("held_step") or journey.get("heldStep")
    stop_step = failed_step or held_step or inst.get("failed_step") or 4

    decisions = inst.get("decisions") or []
    issue = next(
        (d for d in reversed(decisions) if any(
            kw in d.lower() for kw in ("mismatch", "aml", "below", "ambiguity", "failed", "hold", "validate fail", "human review")
        )),
        decisions[-1] if decisions else "Requires human review",
    )

    priority = "HIGH" if stop_step <= 3 else "MEDIUM"
    return {"issue": issue, "failed_step": stop_step, "priority": priority}


class PipelineRunner:
    def __init__(self, graph, session: AsyncSession):
        self.graph = graph
        self.session = session

    async def _broadcast(
        self,
        broadcast: BroadcastFn | None,
        event_type: str,
        instruction_row: InstructionRow,
        workbench_row: WorkbenchRequestRow | None = None,
    ) -> None:
        if not broadcast:
            return
        payload: dict[str, Any] = {
            "type": event_type,
            "id": instruction_row.instruction_id,
            "instruction": instruction_summary(instruction_row),
        }
        if workbench_row:
            payload["workbench"] = workbench_card(workbench_row, instruction_row)
        if instruction_row.is_exception:
            payload["exception"] = exception_summary(instruction_row)
        await broadcast(payload)

    def _instruction_row(self, inst: dict, source_type: str) -> InstructionRow:
        journey = _journey_dict(inst)
        golden_schema = inst.get("golden_schema") or {}
        investor = _investor_name(inst)
        timeline = list(inst.get("timeline") or [])
        exception = _build_exception(inst)
        filename = inst.get("filename") or ""

        return InstructionRow(
            instruction_id=inst["instruction_id"],
            filename=filename or None,
            intent=inst.get("intent"),
            channel=normalize_source_label(inst.get("channel"), source_type),
            routing_target=inst.get("destination"),
            confidence=round_confidence(inst.get("overall_confidence", 0)),
            status=inst.get("status", "Processing"),
            journey=journey,
            golden_schema=golden_schema,
            intake_json=inst.get("intake_json"),
            party=investor if investor != "Unknown" else (filename or "Incoming file"),
            amount_display=format_amount_display(golden_schema) if golden_schema else None,
            field_confidences=inst.get("field_confidences", {}),
            decisions=inst.get("decisions", []),
            repair_notes=inst.get("repair_notes", []),
            timeline=timeline,
            in_queue=True,
            is_exception=bool(exception),
            exception=exception,
            source_type=source_type,
            workbench_stage=inst.get("workbench_stage", "submitted"),
            recon_status=inst.get("recon_status"),
            recon_detail=inst.get("recon_detail"),
        )

    async def _upsert_workbench(
        self,
        inst: dict,
        source_type: str,
        journey: dict,
        timeline: list,
        exception: dict | None,
    ) -> WorkbenchRequestRow | None:
        if not inst.get("needs_human_review"):
            return None

        wb_repo = WorkbenchRepository(self.session)
        existing = await wb_repo.get_by_ref(inst["instruction_id"])
        investor = _investor_name(inst)
        source_label = format_source_label(source_type, inst.get("channel", ""))
        amount_display = format_amount_display(inst.get("golden_schema") or {})

        if existing:
            existing.stage = inst.get("workbench_stage", existing.stage)
            existing.intent = inst.get("intent") or existing.intent
            existing.source = source_label
            existing.party = investor
            existing.amount = amount_display or existing.amount
            existing.confidence = round_confidence(inst.get("overall_confidence", existing.confidence))
            existing.risk = inst.get("risk_score", existing.risk)
            existing.risk_label = inst.get("risk_label", existing.risk_label)
            existing.journey = journey
            existing.fields = inst.get("field_confidences", existing.fields)
            existing.findings = inst.get("findings", existing.findings)
            existing.explain = inst.get("explainability", existing.explain)
            existing.timeline = timeline
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        row = WorkbenchRequestRow(
            id=req_id,
            ref=inst["instruction_id"],
            stage=inst.get("workbench_stage", "review"),
            intent=inst.get("intent") or "Unknown",
            source=source_label,
            party=investor,
            amount=amount_display,
            confidence=round_confidence(inst.get("overall_confidence", 0)),
            risk=inst.get("risk_score", 0),
            risk_label=inst.get("risk_label", "Low"),
            assignee=settings.default_user,
            journey=journey,
            fields=inst.get("field_confidences", {}),
            findings=inst.get("findings", []),
            explain=inst.get("explainability", ""),
            timeline=timeline,
        )
        await wb_repo.save(row)
        logger.info(
            "Workbench request created: req_id=%s instruction_id=%s",
            req_id,
            inst["instruction_id"],
        )
        return row

    async def _sync_workbench_if_exists(
        self,
        inst: dict,
        source_type: str,
        journey: dict,
        timeline: list,
    ) -> WorkbenchRequestRow | None:
        """Keep workbench row in sync after approval when pipeline continues."""
        wb_repo = WorkbenchRepository(self.session)
        existing = await wb_repo.get_by_ref(inst["instruction_id"])
        if not existing:
            return None

        investor = _investor_name(inst)
        source_label = format_source_label(source_type, inst.get("channel", ""))
        amount_display = format_amount_display(inst.get("golden_schema") or {})

        existing.stage = inst.get("workbench_stage", existing.stage)
        existing.intent = inst.get("intent") or existing.intent
        existing.source = source_label
        existing.party = investor
        existing.amount = amount_display or existing.amount
        existing.confidence = round_confidence(inst.get("overall_confidence", existing.confidence))
        existing.journey = journey
        existing.timeline = timeline
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def _persist_progress(
        self,
        state: dict,
        source_type: str,
        broadcast: BroadcastFn | None,
        *,
        processing: bool = False,
        node_name: str | None = None,
    ) -> InstructionRow:
        inst = dict(state.get("instruction") or {})
        inst["needs_human_review"] = state.get("needs_human_review", inst.get("needs_human_review", False))
        journey = _journey_dict(inst)
        timeline = list(inst.get("timeline") or [])
        exception = _build_exception(inst)

        inst_repo = InstructionRepository(self.session)
        row = self._instruction_row(inst, source_type)
        if processing and not exception:
            row.is_exception = False

        existing = await inst_repo.get(row.instruction_id)
        if existing:
            for field in (
                "filename", "intent", "channel", "routing_target", "confidence", "status", "journey",
                "golden_schema", "intake_json", "party", "amount_display", "field_confidences",
                "decisions", "repair_notes", "timeline", "in_queue", "is_exception", "exception",
                "workbench_stage", "recon_status", "recon_detail",
            ):
                setattr(existing, field, getattr(row, field))
            await self.session.commit()
            await self.session.refresh(existing)
            saved = existing
        else:
            saved = await inst_repo.save(row)

        workbench_row = None
        if inst.get("needs_human_review"):
            workbench_row = await self._upsert_workbench(inst, source_type, journey, timeline, exception)
        else:
            workbench_row = await self._sync_workbench_if_exists(inst, source_type, journey, timeline)

        event_type = "instruction_progress" if processing else "instruction_updated"
        await self._broadcast(broadcast, event_type, saved, workbench_row)

        if node_name:
            logger.info(
                "Pipeline progress [%s]: id=%s status=%s journey=%s needs_review=%s",
                node_name,
                saved.instruction_id,
                saved.status,
                journey.get("active_step") or journey.get("held_step") or journey.get("failed_step"),
                inst.get("needs_human_review"),
            )
        return saved

    async def run(
        self,
        raw: bytes,
        source_type: str,
        filename: str,
        broadcast: BroadcastFn | None = None,
    ) -> dict:
        source_type = normalize_source_type(source_type)
        instruction_id = f"INS-{uuid.uuid4().hex[:7].upper()}"
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        initial = {
            "instruction": {
                "_raw": raw,
                "source_type": source_type,
                "filename": filename,
                "instruction_id": instruction_id,
            },
            "needs_human_review": False,
            "approved": False,
        }
        logger.info(
            "Pipeline started: instruction_id=%s filename=%s source_type=%s size=%d bytes thread_id=%s",
            instruction_id,
            filename or "(unnamed)",
            source_type,
            len(raw),
            thread_id,
        )

        await self._persist_progress(
            {
                "instruction": {
                    "instruction_id": instruction_id,
                    "filename": filename,
                    "channel": source_type,
                    "status": "Processing",
                    "journey": {"active_step": 1, "completed_through": 0},
                    "timeline": [],
                },
                "needs_human_review": False,
            },
            source_type,
            broadcast,
            processing=True,
            node_name="started",
        )

        final_state = initial
        try:
            async for update in self.graph.astream(initial, config, stream_mode="updates"):
                for node_name, node_output in update.items():
                    final_state = {**final_state, **node_output}
                    await self._persist_progress(
                        final_state,
                        source_type,
                        broadcast,
                        processing=True,
                        node_name=node_name,
                    )
        except Exception as exc:
            logger.exception(
                "Pipeline failed: instruction_id=%s filename=%s source_type=%s thread_id=%s",
                instruction_id,
                filename or "(unnamed)",
                source_type,
                thread_id,
            )
            issue = f"Ingestion failed: {filename}" if filename else "Pipeline execution failed"
            await InstructionRepository(self.session).update(
                instruction_id,
                status="Failed",
                filename=filename or None,
                party=filename or None,
                journey={"failed_step": 1, "completed_through": 0},
                is_exception=True,
                exception={"issue": issue, "failed_step": 1, "priority": "HIGH"},
            )
            if broadcast:
                row = await InstructionRepository(self.session).get(instruction_id)
                if row:
                    await self._broadcast(broadcast, "instruction_updated", row)
            return {
                "instruction_id": instruction_id,
                "status": "Failed",
                "needs_human_review": False,
                "success": False,
                "error": "Pipeline execution failed",
            }

        inst = final_state["instruction"]
        journey = _journey_dict(inst)
        needs_human_review = final_state.get("needs_human_review", inst.get("needs_human_review", False))

        saved = await self._persist_progress(
            final_state,
            source_type,
            broadcast,
            processing=False,
            node_name="completed",
        )

        logger.info(
            "Pipeline completed: id=%s status=%s needs_human_review=%s journey_step=%s",
            saved.instruction_id,
            saved.status,
            needs_human_review,
            journey.get("held_step") or journey.get("failed_step") or journey.get("active_step"),
        )
        return {
            "instruction_id": saved.instruction_id,
            "status": saved.status,
            "needs_human_review": needs_human_review,
            "success": True,
            "error": None,
        }

    @staticmethod
    def _row_to_instruction_dict(row: InstructionRow) -> dict:
        return {
            "instruction_id": row.instruction_id,
            "filename": row.filename or "",
            "channel": row.channel or "",
            "source_type": row.source_type or "",
            "intake_json": row.intake_json or {},
            "intent": row.intent,
            "destination": row.routing_target,
            "golden_schema": row.golden_schema or {},
            "field_confidences": row.field_confidences or {},
            "overall_confidence": row.confidence,
            "journey": dict(row.journey or {}),
            "workbench_stage": row.workbench_stage or "review",
            "status": row.status,
            "decisions": list(row.decisions or []),
            "repair_notes": list(row.repair_notes or []),
            "timeline": list(row.timeline or []),
            "needs_human_review": False,
            "recon_status": row.recon_status,
            "recon_detail": row.recon_detail,
        }

    async def resume_after_approval(
        self,
        instruction_id: str,
        fields: dict[str, str] | None = None,
        note: str | None = None,
        broadcast: BroadcastFn | None = None,
    ) -> dict:
        """Continue route + reconcile after human workbench approval."""
        inst_repo = InstructionRepository(self.session)
        row = await inst_repo.get(instruction_id)
        if not row:
            return {"success": False, "error": "Instruction not found"}

        inst = self._row_to_instruction_dict(row)
        source_type = normalize_source_type(row.source_type or "pdf")

        if fields:
            golden = dict(inst.get("golden_schema") or {})
            golden.update(fields)
            inst["golden_schema"] = golden
            inst["decisions"].append(f"Human corrections applied: {', '.join(fields.keys())}")

        timeline = list(inst.get("timeline") or [])
        append_timeline(timeline, "Human review approved — continuing to Routing")
        if note:
            timeline.append(note)
        inst["timeline"] = timeline
        inst["needs_human_review"] = False
        inst["workbench_stage"] = "approved"
        inst["journey"] = {"completed_through": 4, "active_step": 5, "held_step": None}
        inst["decisions"].append("Human review approved — proceeding to route and reconcile")

        state: dict = {
            "instruction": inst,
            "needs_human_review": False,
            "approved": True,
        }

        logger.info("Resuming pipeline after approval: instruction_id=%s", instruction_id)

        for node_name, node_fn in (("route", route_node), ("reconcile", reconcile_node)):
            state = await node_fn(state)
            await self._persist_progress(
                state,
                source_type,
                broadcast,
                processing=True,
                node_name=node_name,
            )

        saved = await self._persist_progress(
            state,
            source_type,
            broadcast,
            processing=False,
            node_name="resume_completed",
        )

        logger.info(
            "Pipeline resumed: instruction_id=%s status=%s",
            saved.instruction_id,
            saved.status,
        )
        return {
            "instruction_id": saved.instruction_id,
            "status": saved.status,
            "needs_human_review": False,
            "success": True,
            "error": None,
        }
