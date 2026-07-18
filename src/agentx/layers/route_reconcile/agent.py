from agentx.domain.models import InstructionState, JourneyState
from agentx.shared.mocks import external_apis as mocks


class RouteReconcileAgent:
    async def run(self, state: InstructionState) -> InstructionState:
        dest = state.destination or "TA"
        dispatch = {"TA": mocks.dispatch_ta, "FA": mocks.dispatch_fa, "IS": mocks.dispatch_is}
        result = await dispatch.get(dest, mocks.dispatch_ta)(state.instruction_id)
        state.decisions.append(f"Routed to {dest} — ref {result['ref']}")
        state.journey = JourneyState(completed_through=5, active_step=6)
        state.status = "Routed"

        amount = state.golden_schema.get("amount") or 0
        settlement = await mocks.fetch_settlement(state.instruction_id, float(amount or 0))
        if settlement["matched"]:
            state.journey = JourneyState(state="completed", completed_through=6)
            state.status = "Reconciled"
            state.decisions.append("Reconciliation matched")
        else:
            state.journey = JourneyState(failed_step=6, completed_through=5)
            state.status = "Recon Exception"
            state.needs_human_review = True
            state.workbench_stage = "review"
            state.decisions.append(
                f"Recon mismatch: expected {settlement['expected']}, got {settlement['actual']}"
            )
        return state
