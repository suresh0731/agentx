from agentx.db.schema import InstructionRow, WorkbenchRequestRow


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
        "source": row.channel,
        "intent": row.intent,
        "dest": row.routing_target,
        "conf": f"{row.confidence:.1f}%",
        "confValue": row.confidence,
        "status": row.status,
        "journey": journey_to_api(row.journey or {}),
    }


def instruction_detail(row: InstructionRow) -> dict:
    return {
        "ref": row.instruction_id,
        "meta": row.meta,
        "stage_label": row.stage_label,
        "confidence": row.confidence,
        "recon_status": row.recon_status,
        "recon_detail": row.recon_detail,
        "golden_schema": row.golden_schema,
        "intake": row.intake_json,
        "party": row.party,
        "account": row.account,
        "settlement": row.settlement_display,
        "amount": row.amount_display or str(row.amount or "—"),
        "units": str(row.quantity or "—"),
        "decisions": row.decisions,
        "repair_notes": row.repair_notes,
        "field_confidences": row.field_confidences,
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


def workbench_card(row: WorkbenchRequestRow) -> dict:
    return {
        "id": row.id,
        "ref": row.ref,
        "stage": row.stage,
        "intent": row.intent,
        "source": row.source,
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
        "fields": row.fields,
        "findings": row.findings,
        "explain": row.explain,
        "timeline": row.timeline,
        "comments": row.comments,
    }
