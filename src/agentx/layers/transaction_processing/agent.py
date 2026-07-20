import logging
from types import SimpleNamespace

from agentx.config import settings
from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import (
    DEST_MAP,
    DOC_TYPE_DETECT_MAP,
    append_timeline,
    build_golden_schema,
    classify_intent,
    compute_risk_score,
    extract_doc_type,
    overall_confidence_from_fields,
    round_confidence,
    parse_extraction_fields,
)
from agentx.layers.transaction_processing.validation import validate_fund_transaction
from agentx.shared.mocks import external_apis as mocks

logger = logging.getLogger(__name__)

VALIDATION_CTX_KEY = "_validation"

INTENT_MAP = {
    "subscription": "Subscription",
    "redemption": "Redemption",
    "switch": "Switch",
    "transfer": "Transfer",
}


def _has_idp_extraction(state: InstructionState) -> bool:
    intake = state.intake_json
    return bool(intake.get("extraction_result") or intake.get("idp_raw"))


def _parse_idp_fields(state: InstructionState) -> tuple[dict, dict[str, float]]:
    extraction = state.intake_json.get("extraction_result") or {}
    values, parsed_confidences = parse_extraction_fields(extraction)
    field_confidences = state.intake_json.get("field_confidences") or parsed_confidences
    return values, field_confidences


def _store_validation_report(state: InstructionState, report) -> None:
    state.intake_json[VALIDATION_CTX_KEY] = {
        "failed_fields": list(report.failed_fields),
        "human_review_fields": list(report.human_review_fields),
        "passed": report.passed,
    }


def _load_validation_report(state: InstructionState) -> SimpleNamespace:
    ctx = state.intake_json.get(VALIDATION_CTX_KEY) or {}
    return SimpleNamespace(
        failed_fields=ctx.get("failed_fields", []),
        human_review_fields=ctx.get("human_review_fields", []),
        passed=ctx.get("passed", True),
    )


class TransactionProcessingAgent:
    async def detect(self, state: InstructionState) -> InstructionState:
        if _has_idp_extraction(state):
            return self._detect_idp(state)
        return await self._detect_legacy(state)

    async def validate(self, state: InstructionState) -> InstructionState:
        if _has_idp_extraction(state):
            return self._validate_idp(state)
        return await self._validate_legacy(state)

    async def repair(self, state: InstructionState) -> InstructionState:
        if _has_idp_extraction(state):
            return self._repair_idp(state)
        return self._repair_legacy(state)

    async def run(self, state: InstructionState) -> InstructionState:
        """Run all three stages sequentially (used by tests and direct invocation)."""
        state = await self.detect(state)
        state = await self.validate(state)
        return await self.repair(state)

    def _detect_idp(self, state: InstructionState) -> InstructionState:
        logger.info("Detect (IDP): instruction_id=%s", state.instruction_id)
        values, _ = _parse_idp_fields(state)
        intake = state.intake_json
        doc_type = intake.get("doc_type") or (intake.get("transaction") or {}).get("doc_type")
        if not doc_type and intake.get("idp_raw"):
            doc_type = extract_doc_type(intake["idp_raw"])

        doc_type_key = (doc_type or "").lower()
        classification = DOC_TYPE_DETECT_MAP.get(doc_type_key, doc_type or "Unknown")

        transaction_type = values.get("transaction_type")
        state.intent = classify_intent(transaction_type)
        state.destination = DEST_MAP.get(state.intent, "TA")

        state.journey = JourneyState(completed_through=2, active_step=3)
        append_timeline(state.timeline, f"Detect & Classify: {classification}")
        state.decisions.append(f"Document type: {doc_type or 'unknown'} → {classification}")
        state.decisions.append(f"Intent classified: {state.intent} (IDP)")
        logger.info(
            "Detect complete: instruction_id=%s doc_type=%s classification=%s intent=%s",
            state.instruction_id,
            doc_type,
            classification,
            state.intent,
        )
        return state

    async def _detect_legacy(self, state: InstructionState) -> InstructionState:
        logger.info("Detect (legacy): instruction_id=%s", state.instruction_id)
        txn = state.intake_json.get("transaction", {})
        hint = (txn.get("intentHint") or "subscription").lower()
        state.intent = INTENT_MAP.get(hint, "Subscription")
        state.destination = DEST_MAP.get(state.intent, "TA")
        state.journey = JourneyState(completed_through=2, active_step=3)
        append_timeline(state.timeline, f"Detect & Classify: {state.intent}")
        state.decisions.append(f"Intent classified: {state.intent}")
        return state

    def _validate_idp(self, state: InstructionState) -> InstructionState:
        logger.info("Validate (IDP): instruction_id=%s", state.instruction_id)
        values, field_confidences = _parse_idp_fields(state)
        report = validate_fund_transaction(values, field_confidences)
        _store_validation_report(state, report)

        for result in report.field_results:
            if result.passed:
                state.decisions.append(f"Validate: {result.field} — {result.message}")
            else:
                state.decisions.append(f"Validate FAIL: {result.field} — {result.message}")

        if report.failed_fields:
            append_timeline(
                state.timeline,
                f"Validate & Enrich: {len(report.failed_fields)} field(s) failed rules",
            )
            logger.warning(
                "Validation failures: instruction_id=%s fields=%s",
                state.instruction_id,
                ", ".join(report.failed_fields),
            )
        else:
            append_timeline(state.timeline, "Validate & Enrich passed")

        state.journey = JourneyState(completed_through=3, active_step=4)
        logger.info(
            "Validate complete: instruction_id=%s passed=%s failed=%s human_review=%s",
            state.instruction_id,
            report.passed,
            report.failed_fields,
            report.human_review_fields,
        )
        return state

    async def _validate_legacy(self, state: InstructionState) -> InstructionState:
        logger.info("Validate (legacy): instruction_id=%s", state.instruction_id)
        txn = state.intake_json.get("transaction", {})
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
        if not aml["clear"]:
            state.decisions.append("AML API: Enhanced due diligence required")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=3, completed_through=2)
            append_timeline(state.timeline, "Validate & Enrich: AML hold")
        else:
            state.decisions.append("AML API: Clear")
            append_timeline(state.timeline, "Validate & Enrich passed")
            state.journey = JourneyState(completed_through=3, active_step=4)

        state.intake_json[VALIDATION_CTX_KEY] = {
            "failed_fields": [],
            "human_review_fields": [],
            "passed": not state.needs_human_review,
        }
        return state

    def _repair_idp(self, state: InstructionState) -> InstructionState:
        logger.info("Repair (IDP): instruction_id=%s", state.instruction_id)
        values, field_confidences = _parse_idp_fields(state)
        validation_report = _load_validation_report(state)

        state.field_confidences = field_confidences
        state.golden_schema = build_golden_schema(
            state.instruction_id,
            values,
            state.destination,
        )
        state.overall_confidence = overall_confidence_from_fields(field_confidences)
        state.repair_notes.append("Repair bypassed — auto-success (repair logic pending)")
        append_timeline(state.timeline, "Repair + Templatise (bypassed — auto-success)")

        needs_review = bool(
            validation_report.human_review_fields
            or validation_report.failed_fields
        )
        if needs_review:
            state.needs_human_review = True
            state.workbench_stage = "review"
            state.journey = JourneyState(held_step=4, completed_through=3)

            review_fields = (
                validation_report.human_review_fields or validation_report.failed_fields
            )
            append_timeline(state.timeline, "Routed to Human Review queue")
            state.decisions.append(
                f"Human review required — fields: {', '.join(review_fields)}"
            )
            if validation_report.human_review_fields:
                state.decisions.append(
                    "Null value or zero confidence on: "
                    + ", ".join(validation_report.human_review_fields)
                )
        else:
            state.journey = JourneyState(completed_through=4, active_step=5)
            state.decisions.append("Repair: bypassed with success — proceeding to routing")

        state.risk_score, state.risk_label = compute_risk_score(values, field_confidences)
        state.findings = state.decisions.copy()
        state.explainability = (
            f"Processed {state.intent} from IDP extraction with "
            f"{state.overall_confidence:.1f}% average field confidence."
        )
        logger.info(
            "Repair complete: instruction_id=%s needs_review=%s risk=%s",
            state.instruction_id,
            state.needs_human_review,
            state.risk_label,
        )
        return state

    def _repair_legacy(self, state: InstructionState) -> InstructionState:
        logger.info("Repair (legacy): instruction_id=%s", state.instruction_id)
        if state.journey.held_step == 3:
            logger.info("Repair skipped — held at validate: instruction_id=%s", state.instruction_id)
            return state

        txn = state.intake_json.get("transaction", {})
        isin = txn.get("isin", "")
        account = state.intake_json.get("party", {}).get("accountId", "")
        party = state.intake_json.get("party", {}).get("name", "")

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
        state.overall_confidence = (
            round_confidence(sum(confidences) / len(confidences)) if confidences else 92.0
        )

        if txn.get("quantity") is None and state.intent == "Switch":
            state.overall_confidence = 87.2
            state.field_confidences["amount_unit"] = 72.0
            state.repair_notes.append("Quantity ambiguity — suggested repair from NAV")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=4, completed_through=3)
            append_timeline(state.timeline, "Repair held — quantity ambiguity")
        else:
            state.repair_notes.append("Templatised to Golden Schema")
            state.journey = JourneyState(completed_through=4, active_step=5)
            append_timeline(state.timeline, "Repair + Templatise")

        if state.overall_confidence < settings.confidence_gate * 100:
            state.needs_human_review = True
            state.workbench_stage = "review"
            if not state.journey.held_step:
                state.journey = JourneyState(held_step=4, completed_through=3)
            append_timeline(state.timeline, "Routed to Human Review queue (<98%)")
            state.decisions.append(
                f"Confidence {state.overall_confidence:.1f}% — below 98% gate"
            )

        state.risk_score, state.risk_label = compute_risk_score(
            state.golden_schema, state.field_confidences
        )
        state.findings = state.decisions.copy()
        state.explainability = f"Processed {state.intent} via Detect→Validate→Repair."
        return state
