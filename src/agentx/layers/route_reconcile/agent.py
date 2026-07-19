import logging

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import append_timeline, parse_amount_nominal
from agentx.shared.mocks import external_apis as mocks

logger = logging.getLogger(__name__)


class RouteReconcileAgent:
    async def run(self, state: InstructionState) -> InstructionState:
        dest = state.destination or "TA"
        logger.info("Routing instruction_id=%s to destination=%s", state.instruction_id, dest)
        dispatch = {"TA": mocks.dispatch_ta, "FA": mocks.dispatch_fa, "IS": mocks.dispatch_is}
        result = await dispatch.get(dest, mocks.dispatch_ta)(state.instruction_id)
        state.decisions.append(f"Routed to {dest} — ref {result['ref']}")
        state.journey = JourneyState(completed_through=5, active_step=6)
        append_timeline(state.timeline, f"Routed to {dest}")
        state.status = "Routed"
        logger.info("Dispatch complete: instruction_id=%s dest=%s ref=%s", state.instruction_id, dest, result["ref"])

        amount = (
            parse_amount_nominal(state.golden_schema.get("amount_nominal"))
            or state.golden_schema.get("amount")
            or 0
        )
        logger.debug("Reconciling instruction_id=%s amount=%s", state.instruction_id, amount)
        settlement = await mocks.fetch_settlement(state.instruction_id, float(amount or 0))
        if settlement["matched"]:
            state.journey = JourneyState(state="completed", completed_through=6)
            state.status = "Reconciled"
            state.decisions.append("Reconciliation matched")
            append_timeline(state.timeline, "Reconciliation matched")
            logger.info("Reconciliation matched: instruction_id=%s amount=%s", state.instruction_id, amount)
        else:
            state.journey = JourneyState(failed_step=6, completed_through=5)
            state.status = "Recon Exception"
            state.needs_human_review = True
            state.workbench_stage = "review"
            append_timeline(state.timeline, "Reconciliation mismatch")
            state.decisions.append(
                f"Recon mismatch: expected {settlement['expected']}, got {settlement['actual']}"
            )
            logger.warning(
                "Reconciliation mismatch: instruction_id=%s expected=%s actual=%s",
                state.instruction_id,
                settlement["expected"],
                settlement["actual"],
            )
        return state
