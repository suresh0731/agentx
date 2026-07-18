from agentx.config import settings
from agentx.domain.models import InstructionState, JourneyState
from agentx.shared.mocks import external_apis as mocks


INTENT_MAP = {
    "subscription": "Subscription",
    "redemption": "Redemption",
    "switch": "Switch",
    "transfer": "Transfer",
}

DEST_MAP = {
    "Subscription": "TA",
    "Redemption": "FA",
    "Switch": "TA",
    "Transfer": "IS",
}


class TransactionProcessingAgent:
    async def run(self, state: InstructionState) -> InstructionState:
        txn = state.intake_json.get("transaction", {})
        hint = (txn.get("intentHint") or "subscription").lower()
        state.intent = INTENT_MAP.get(hint, "Subscription")
        state.destination = DEST_MAP.get(state.intent, "TA")
        state.journey = JourneyState(completed_through=2, active_step=3)
        state.decisions.append(f"Intent classified: {state.intent}")

        isin = txn.get("isin", "")
        account = state.intake_json.get("party", {}).get("accountId", "")
        if isin:
            fund = await mocks.fund_lookup(isin)
            if fund:
                state.decisions.append("Fund API: ISIN valid")
                state.field_confidences["ISIN"] = 96.0
            else:
                state.field_confidences["ISIN"] = 45.0
                state.failed_step = 3
                state.needs_human_review = True
        if account:
            inv = await mocks.investor_verify(account)
            if inv.get("active"):
                state.decisions.append("Investor API: Account active")
                state.field_confidences["Investor"] = 95.0

        party = state.intake_json.get("party", {}).get("name", "")
        aml = await mocks.aml_screen(party)
        if not aml["clear"]:
            state.decisions.append("AML API: Enhanced due diligence required")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=3, completed_through=2)
        else:
            state.decisions.append("AML API: Clear")

        state.journey = JourneyState(completed_through=3, active_step=4)
        amount = txn.get("amount")
        state.golden_schema = {
            "instructionId": state.instruction_id,
            "intent": state.intent.upper(),
            "currency": txn.get("currency", "USD"),
            "party": party or txn.get("party"),
            "amount": amount,
            "quantity": txn.get("quantity"),
            "isin": isin or None,
            "routingTarget": state.destination,
        }
        confidences = [v for v in state.field_confidences.values() if v > 0]
        state.overall_confidence = sum(confidences) / len(confidences) if confidences else 92.0
        if txn.get("quantity") is None and state.intent == "Switch":
            state.overall_confidence = 87.2
            state.field_confidences["Quantity"] = 72.0
            state.repair_notes.append("Quantity ambiguity — suggested repair from NAV")
            state.needs_human_review = True
            state.journey = JourneyState(held_step=4, completed_through=3)
        else:
            state.repair_notes.append("Templatised to Golden Schema")
            state.journey = JourneyState(completed_through=4, active_step=5)

        if state.overall_confidence < settings.confidence_gate * 100:
            state.needs_human_review = True
            state.workbench_stage = "review"
            state.decisions.append(f"Confidence {state.overall_confidence:.1f}% — below 98% gate")

        state.findings = state.decisions.copy()
        state.explainability = f"Processed {state.intent} via Detect→Validate→Repair."
        return state
