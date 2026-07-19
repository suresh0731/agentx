import logging

from agentx.config import settings
from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import (
    DEST_MAP,
    append_timeline,
    build_golden_schema,
    classify_intent,
    compute_risk_score,
    overall_confidence_from_fields,
    parse_extraction_fields,
)
from agentx.shared.mocks import external_apis as mocks

logger = logging.getLogger(__name__)


INTENT_MAP = {
    "subscription": "Subscription",
    "redemption": "Redemption",
    "switch": "Switch",
    "transfer": "Transfer",
}


class TransactionProcessingAgent:
    def _has_idp_extraction(self, state: InstructionState) -> bool:
        intake = state.intake_json
        return bool(intake.get("extraction_result") or intake.get("idp_raw"))

    async def _run_idp_path(self, state: InstructionState) -> InstructionState:
        logger.info("IDP transaction processing: instruction_id=%s", state.instruction_id)
        extraction = state.intake_json.get("extraction_result") or {}
        values, parsed_confidences = parse_extraction_fields(extraction)
        field_confidences = state.intake_json.get("field_confidences") or parsed_confidences

        transaction_type = values.get("transaction_type")
        state.intent = classify_intent(transaction_type)
        state.destination = DEST_MAP.get(state.intent, "TA")
        state.journey = JourneyState(completed_through=2, active_step=3)
        append_timeline(state.timeline, f"Detect & Classify: {state.intent}")
        state.decisions.append(f"Intent classified: {state.intent} (IDP)")

        party = values.get("investor_account_name") or state.intake_json.get("party", {}).get("name", "")
        aml = await mocks.aml_screen(party or "Unknown")
        aml_hold = False
        if not aml["clear"]:
            state.decisions.append("AML API: Enhanced due diligence required")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=3, completed_through=2)
            append_timeline(state.timeline, "Validate & Enrich: AML hold")
            aml_hold = True
            logger.warning("AML hold (IDP): instruction_id=%s party=%s", state.instruction_id, party or "Unknown")
        else:
            state.decisions.append("AML API: Clear")
            append_timeline(state.timeline, "Validate & Enrich passed")

        state.field_confidences = field_confidences
        state.golden_schema = build_golden_schema(
            state.instruction_id,
            values,
            state.destination,
        )
        state.overall_confidence = overall_confidence_from_fields(field_confidences)
        if not aml_hold:
            state.journey = JourneyState(completed_through=4, active_step=5)
        state.repair_notes.append("Templatised to Golden Schema from IDP extraction")
        append_timeline(state.timeline, "Repair + Templatise (IDP)")

        low_fields = [
            field for field, score in field_confidences.items()
            if field != "document_confidence_score" and score < settings.confidence_gate * 100
        ]
        if low_fields:
            state.needs_human_review = True
            state.workbench_stage = "review"
            state.journey = JourneyState(held_step=4, completed_through=3)
            append_timeline(state.timeline, "Repair held — low-confidence fields")
            logger.warning(
                "Low-confidence fields: instruction_id=%s fields=%s",
                state.instruction_id,
                ", ".join(low_fields),
            )
            state.decisions.append(
                f"Fields below {settings.confidence_gate * 100:.0f}% gate: {', '.join(low_fields)}"
            )

        if state.overall_confidence < settings.confidence_gate * 100:
            state.needs_human_review = True
            state.workbench_stage = "review"
            if not state.journey.held_step:
                state.journey = JourneyState(held_step=4, completed_through=3)
            append_timeline(state.timeline, "Routed to Human Review queue (<98%)")
            state.decisions.append(
                f"Overall confidence {state.overall_confidence:.1f}% — below {settings.confidence_gate * 100:.0f}% gate"
            )

        state.risk_score, state.risk_label = compute_risk_score(values, field_confidences)
        state.findings = state.decisions.copy()
        state.explainability = (
            f"Processed {state.intent} from IDP extraction with "
            f"{state.overall_confidence:.1f}% average field confidence."
        )
        logger.info(
            "IDP processing complete: instruction_id=%s intent=%s confidence=%.1f risk=%s (%s) needs_review=%s",
            state.instruction_id,
            state.intent,
            state.overall_confidence,
            state.risk_score,
            state.risk_label,
            state.needs_human_review,
        )
        return state

    async def _run_legacy_path(self, state: InstructionState) -> InstructionState:
        logger.info("Legacy transaction processing: instruction_id=%s", state.instruction_id)
        txn = state.intake_json.get("transaction", {})
        hint = (txn.get("intentHint") or "subscription").lower()
        state.intent = INTENT_MAP.get(hint, "Subscription")
        state.destination = DEST_MAP.get(state.intent, "TA")
        state.journey = JourneyState(completed_through=2, active_step=3)
        append_timeline(state.timeline, f"Detect & Classify: {state.intent}")
        state.decisions.append(f"Intent classified: {state.intent}")

        isin = txn.get("isin", "")
        account = state.intake_json.get("party", {}).get("accountId", "")
        if isin:
            fund = await mocks.fund_lookup(isin)
            if fund:
                state.decisions.append("Fund API: ISIN valid")
                state.field_confidences["fund_code"] = 96.0
            else:
                state.field_confidences["fund_code"] = 45.0
                state.failed_step = 3
                state.needs_human_review = True
        if account:
            inv = await mocks.investor_verify(account)
            if inv.get("active"):
                state.decisions.append("Investor API: Account active")
                state.field_confidences["investor_account_name"] = 95.0

        party = state.intake_json.get("party", {}).get("name", "")
        aml = await mocks.aml_screen(party)
        aml_hold = False
        if not aml["clear"]:
            state.decisions.append("AML API: Enhanced due diligence required")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=3, completed_through=2)
            append_timeline(state.timeline, "Validate & Enrich: AML hold")
            aml_hold = True
        else:
            state.decisions.append("AML API: Clear")
            append_timeline(state.timeline, "Validate & Enrich passed")

        if not aml_hold:
            state.journey = JourneyState(completed_through=3, active_step=4)
        state.golden_schema = {
            "country": None,
            "transaction_date": txn.get("settlementDate"),
            "transaction_type": state.intent.upper(),
            "switch_transaction": "YES" if state.intent == "Switch" else "NO",
            "reference_no": None,
            "sid": None,
            "fundcd_type": None,
            "fund_code": isin or None,
            "fund_currency": txn.get("currency", "USD"),
            "amount_nominal": txn.get("amount"),
            "amount_unit": txn.get("quantity"),
            "amount_all_units": None,
            "sa_reference_no": account or None,
            "investor_account_name": party or txn.get("party"),
        }
        confidences = [v for v in state.field_confidences.values() if v > 0]
        state.overall_confidence = sum(confidences) / len(confidences) if confidences else 92.0
        if txn.get("quantity") is None and state.intent == "Switch":
            state.overall_confidence = 87.2
            state.field_confidences["amount_unit"] = 72.0
            state.repair_notes.append("Quantity ambiguity — suggested repair from NAV")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=4, completed_through=3)
            append_timeline(state.timeline, "Repair held — quantity ambiguity")
        else:
            state.repair_notes.append("Templatised to Golden Schema")
            if not aml_hold:
                state.journey = JourneyState(completed_through=4, active_step=5)
            append_timeline(state.timeline, "Repair + Templatise")

        if state.overall_confidence < settings.confidence_gate * 100:
            state.needs_human_review = True
            state.workbench_stage = "review"
            if not state.journey.held_step:
                state.journey = JourneyState(held_step=4, completed_through=3)
            append_timeline(state.timeline, "Routed to Human Review queue (<98%)")
            state.decisions.append(f"Confidence {state.overall_confidence:.1f}% — below 98% gate")

        state.risk_score, state.risk_label = compute_risk_score(state.golden_schema, state.field_confidences)
        state.findings = state.decisions.copy()
        state.explainability = f"Processed {state.intent} via Detect→Validate→Repair."
        logger.info(
            "Legacy processing complete: instruction_id=%s intent=%s confidence=%.1f needs_review=%s",
            state.instruction_id,
            state.intent,
            state.overall_confidence,
            state.needs_human_review,
        )
        return state

    async def run(self, state: InstructionState) -> InstructionState:
        path = "idp" if self._has_idp_extraction(state) else "legacy"
        logger.debug("Transaction processing path=%s instruction_id=%s", path, state.instruction_id)
        if path == "idp":
            return await self._run_idp_path(state)
        return await self._run_legacy_path(state)
