import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentx.db.schema import (
    Base,
    ConfigRuleRow,
    EvidenceEventRow,
    InstructionRow,
    MetricRollupRow,
    WorkbenchRequestRow,
)
from agentx.layers.ingest.idp_schema import normalize_source_label

logger = logging.getLogger(__name__)

SEED_PATH = Path(__file__).resolve().parents[3] / "seed" / "demo_data.json"


def load_seed_data() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


async def clear_database(session: AsyncSession) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(delete(table))
    await session.commit()


async def seed_database(session: AsyncSession) -> None:
    data = load_seed_data()
    instruction_count = len(data["instructions"])
    workbench_count = len(data["workbench_requests"])
    logger.info(
        "Seeding database: instructions=%d workbench_requests=%d evidence_events=%d",
        instruction_count,
        workbench_count,
        len(data.get("evidence_events", [])),
    )

    for inst in data["instructions"]:
        intake = inst.get("intake") or {}
        source_type = intake.get("source_type")
        session.add(InstructionRow(
            instruction_id=inst["instruction_id"],
            intent=inst.get("intent"),
            channel=normalize_source_label(inst.get("channel"), source_type),
            routing_target=inst.get("routing_target"),
            confidence=inst.get("confidence", 0.0),
            status=inst.get("status", "Processing"),
            status_tone=inst.get("status_tone"),
            journey=inst.get("journey", {}),
            meta=inst.get("meta"),
            stage_label=inst.get("stage_label"),
            recon_status=inst.get("recon_status"),
            recon_detail=inst.get("recon_detail"),
            golden_schema=inst.get("golden_schema"),
            intake_json=inst.get("intake"),
            party=inst.get("party"),
            account=inst.get("account"),
            settlement_date=inst.get("settlement_date"),
            settlement_display=inst.get("settlement_display"),
            amount=inst.get("amount"),
            amount_display=inst.get("amount_display"),
            quantity=inst.get("quantity"),
            currency=inst.get("currency"),
            decisions=inst.get("decisions", []),
            repair_notes=inst.get("repair_notes", []),
            field_confidences=inst.get("field_confidences", {}),
            timeline=inst.get("timeline", []),
            is_exception=inst.get("is_exception", False),
            exception=inst.get("exception"),
            in_queue=inst.get("in_queue", True),
            workbench_request_id=inst.get("workbench_request_id"),
            source_type=source_type,
            workbench_stage=None,
        ))

    for wb in data["workbench_requests"]:
        session.add(WorkbenchRequestRow(
            id=wb["id"],
            ref=wb["ref"],
            stage=wb["stage"],
            intent=wb["intent"],
            source=normalize_source_label(wb["source"]),
            party=wb["party"],
            amount=wb["amount"],
            confidence=wb["confidence"],
            risk=wb["risk"],
            risk_label=wb["riskLabel"],
            sla_minutes=wb["slaMinutes"],
            sla_remaining=wb["slaRemaining"],
            assignee=wb["assignee"],
            path=wb["path"],
            journey=wb["journey"],
            fields=wb["fields"],
            findings=wb["findings"],
            explain=wb["explain"],
            timeline=wb["timeline"],
            comments=wb["comments"],
        ))

    for ev in data["evidence_events"]:
        session.add(EvidenceEventRow(
            id=ev["id"],
            instruction_id=ev["instruction_id"],
            timestamp=datetime.fromisoformat(ev["timestamp"]),
            stage=ev["stage"],
            stage_label=ev["stage_label"],
            event_type=ev["event_type"],
            summary=ev["summary"],
            detail=ev.get("detail"),
            actor=ev["actor"],
        ))

    rollups = {
        "metric_rollups": data["metric_rollups"],
        "journey_health": data["journey_health"],
        "attention": data["attention"],
        "channels": data["channels"],
        "routing": data["routing"],
        "intents": data["intents"],
        "user": data["user"],
    }
    for key, payload in rollups.items():
        if key == "channels":
            payload = [
                {**ch, "name": normalize_source_label(ch["name"])}
                for ch in payload
            ]
        session.add(MetricRollupRow(key=key, payload=payload))

    for category, rules in data["config_rules"].items():
        session.add(ConfigRuleRow(category=category, rules=rules))

    await session.commit()
    logger.info("Database seed complete: instructions=%d workbench_requests=%d", instruction_count, workbench_count)


async def is_seeded(session: AsyncSession) -> bool:
    result = await session.execute(select(InstructionRow).limit(1))
    return result.scalar_one_or_none() is not None
