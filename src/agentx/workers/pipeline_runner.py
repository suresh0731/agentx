import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from agentx.config import settings
from agentx.db.repositories.instruction_repo import InstructionRepository, WorkbenchRepository
from agentx.db.schema import InstructionRow, WorkbenchRequestRow
from agentx.layers.ingest.idp_schema import format_amount_display, format_source_label, normalize_source_label

logger = logging.getLogger(__name__)


def _journey_dict(inst: dict) -> dict:
    journey = inst.get("journey") or {}
    if hasattr(journey, "model_dump"):
        return journey.model_dump()
    return dict(journey)


def _investor_name(inst: dict) -> str:
    golden = inst.get("golden_schema") or {}
    intake = inst.get("intake_json") or {}
    return (
        golden.get("investor_account_name")
        or intake.get("party", {}).get("name")
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
            kw in d.lower() for kw in ("mismatch", "aml", "below", "ambiguity", "failed", "hold")
        )),
        decisions[-1] if decisions else "Requires human review",
    )

    priority = "HIGH" if stop_step <= 3 else "MEDIUM"
    return {"issue": issue, "failed_step": stop_step, "priority": priority}


class PipelineRunner:
    def __init__(self, graph, session: AsyncSession):
        self.graph = graph
        self.session = session

    async def run(self, raw: bytes, source_type: str, filename: str) -> dict:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        initial = {
            "instruction": {"_raw": raw, "source_type": source_type, "filename": filename},
            "needs_human_review": False,
            "approved": False,
        }
        logger.info(
            "Pipeline started: filename=%s source_type=%s size=%d bytes thread_id=%s",
            filename or "(unnamed)",
            source_type,
            len(raw),
            thread_id,
        )
        try:
            result = await self.graph.ainvoke(initial, config)
        except Exception:
            logger.exception(
                "Pipeline failed: filename=%s source_type=%s thread_id=%s",
                filename or "(unnamed)",
                source_type,
                thread_id,
            )
            return {
                "instruction_id": None,
                "status": "Failed",
                "needs_human_review": False,
                "success": False,
                "error": "Pipeline execution failed",
            }

        inst = result["instruction"]
        instruction_id = inst["instruction_id"]
        journey = _journey_dict(inst)
        golden_schema = inst.get("golden_schema") or {}
        investor = _investor_name(inst)
        source_label = format_source_label(source_type, inst.get("channel", ""))
        amount_display = format_amount_display(golden_schema)
        timeline = list(inst.get("timeline") or [])
        exception = _build_exception(inst)

        inst_repo = InstructionRepository(self.session)
        await inst_repo.save(InstructionRow(
            instruction_id=instruction_id,
            intent=inst.get("intent"),
            channel=normalize_source_label(inst.get("channel"), source_type),
            routing_target=inst.get("destination"),
            confidence=inst.get("overall_confidence", 0),
            status=inst.get("status", "Processing"),
            journey=journey,
            golden_schema=golden_schema,
            intake_json=inst.get("intake_json"),
            party=investor,
            amount_display=amount_display,
            field_confidences=inst.get("field_confidences", {}),
            decisions=inst.get("decisions", []),
            repair_notes=inst.get("repair_notes", []),
            timeline=timeline,
            in_queue=True,
            is_exception=bool(exception),
            exception=exception,
            source_type=source_type,
            workbench_stage=inst.get("workbench_stage", "submitted"),
        ))
        logger.info(
            "Instruction saved: id=%s intent=%s status=%s confidence=%.1f investor=%s source=%s",
            instruction_id,
            inst.get("intent"),
            inst.get("status"),
            inst.get("overall_confidence", 0),
            investor,
            source_label,
        )

        needs_human_review = inst.get("needs_human_review", False)
        if needs_human_review:
            wb_repo = WorkbenchRepository(self.session)
            req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
            await wb_repo.save(WorkbenchRequestRow(
                id=req_id,
                ref=instruction_id,
                stage=inst.get("workbench_stage", "review"),
                intent=inst.get("intent") or "Unknown",
                source=source_label,
                party=investor,
                amount=amount_display,
                confidence=inst.get("overall_confidence", 0),
                risk=inst.get("risk_score", 0),
                risk_label=inst.get("risk_label", "Low"),
                assignee=settings.default_user,
                journey=journey,
                fields=inst.get("field_confidences", {}),
                findings=inst.get("findings", []),
                explain=inst.get("explainability", ""),
                timeline=timeline,
            ))
            logger.info(
                "Workbench request created: req_id=%s instruction_id=%s risk=%s (%s) issue=%s",
                req_id,
                instruction_id,
                inst.get("risk_score", 0),
                inst.get("risk_label", "Low"),
                (exception or {}).get("issue", "human review"),
            )
        elif exception:
            logger.warning(
                "Instruction flagged as exception without workbench: id=%s issue=%s",
                instruction_id,
                exception.get("issue"),
            )

        logger.info(
            "Pipeline completed: id=%s status=%s needs_human_review=%s journey_step=%s",
            instruction_id,
            inst.get("status"),
            needs_human_review,
            journey.get("held_step") or journey.get("failed_step") or journey.get("active_step"),
        )
        return {
            "instruction_id": instruction_id,
            "status": inst.get("status"),
            "needs_human_review": needs_human_review,
            "success": True,
            "error": None,
        }
