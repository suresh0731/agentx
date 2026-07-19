from agentx.db.schema import InstructionRow, WorkbenchRequestRow
from agentx.layers.ingest.idp_schema import (
    IDP_FIELDS,
    normalize_field_confidences,
    normalize_golden_schema,
    normalize_source_label,
    parse_extraction_fields,
)


def journey_to_api(journey: dict) -> dict:
    return {
        "state": journey.get("state"),
        "completedThrough": journey.get("completed_through", journey.get("completedThrough", 0)),
        "activeStep": journey.get("active_step", journey.get("activeStep")),
        "heldStep": journey.get("held_step", journey.get("heldStep")),
        "failedStep": journey.get("failed_step", journey.get("failedStep")),
    }


def instruction_summary(row: InstructionRow) -> dict:
    return {
        "ref": row.instruction_id,
        "source": normalize_source_label(row.channel, row.source_type),
        "intent": row.intent,
        "dest": row.routing_target,
        "conf": f"{row.confidence:.1f}%",
        "confValue": row.confidence,
        "status": row.status,
        "journey": journey_to_api(row.journey or {}),
    }


def _golden_schema_for_row(row: InstructionRow) -> dict:
    intake = row.intake_json or {}
    golden_source = dict(row.golden_schema or {})

    if intake.get("extraction_result"):
        values, _ = parse_extraction_fields(intake["extraction_result"])
        for field, value in values.items():
            if golden_source.get(field) in (None, "") and value not in (None, ""):
                golden_source[field] = value
        if not golden_source:
            golden_source = {"extraction_result": intake["extraction_result"]}

    return normalize_golden_schema(golden_source)


def _field_confidences_for_row(row: InstructionRow) -> dict[str, float]:
    intake = row.intake_json or {}
    field_source: dict[str, float] = {}

    for source in (row.field_confidences, intake.get("field_confidences")):
        if isinstance(source, dict):
            field_source.update(source)

    if intake.get("extraction_result"):
        _, parsed = parse_extraction_fields(intake["extraction_result"])
        for field in IDP_FIELDS:
            if field in parsed:
                field_source[field] = parsed[field]

    return normalize_field_confidences(field_source)


def instruction_detail(row: InstructionRow) -> dict:
    return {
        "ref": row.instruction_id,
        "meta": row.meta,
        "stage_label": row.stage_label,
        "confidence": row.confidence,
        "recon_status": row.recon_status,
        "recon_detail": row.recon_detail,
        "golden_schema": _golden_schema_for_row(row),
        "intake": row.intake_json,
        "party": row.party,
        "account": row.account,
        "settlement": row.settlement_display,
        "amount": row.amount_display or str(row.amount or "—"),
        "units": str(row.quantity or "—"),
        "decisions": row.decisions,
        "repair_notes": row.repair_notes,
        "field_confidences": _field_confidences_for_row(row),
        "timeline": row.timeline,
        "journey": journey_to_api(row.journey or {}),
        "status": row.status,
    }


def exception_summary(row: InstructionRow) -> dict:
    exc = row.exception or {}
    return {
        "ref": row.instruction_id,
        "issue": exc.get("issue", "Exception"),
        "failed_step": exc.get("failed_step", 0),
        "priority": exc.get("priority", "MEDIUM"),
        "journey": journey_to_api(row.journey or {}),
    }


def workbench_card(row: WorkbenchRequestRow, instruction: InstructionRow | None = None) -> dict:
    fields = _field_confidences_for_row(instruction) if instruction is not None else normalize_field_confidences(row.fields)
    if instruction is None and sum(fields.values()) == 0:
        fields = normalize_field_confidences(row.fields)

    payload = {
        "id": row.id,
        "ref": row.ref,
        "stage": row.stage,
        "intent": row.intent,
        "source": normalize_source_label(
            row.source,
            instruction.source_type if instruction is not None else None,
        ),
        "party": row.party,
        "amount": row.amount,
        "confidence": row.confidence,
        "risk": row.risk,
        "riskLabel": row.risk_label,
        "slaMinutes": row.sla_minutes,
        "slaRemaining": row.sla_remaining,
        "assignee": row.assignee,
        "path": row.path,
        "journey": journey_to_api(row.journey or {}),
        "fields": fields,
        "findings": row.findings,
        "explain": row.explain,
        "timeline": row.timeline,
        "comments": row.comments,
    }
    if instruction is not None:
        payload["golden_schema"] = _golden_schema_for_row(instruction)
        payload["intake"] = instruction.intake_json
    return payload
