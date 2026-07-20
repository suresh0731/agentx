import logging

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import append_timeline, parse_amount_nominal
from agentx.shared.mocks import external_apis as mocks

logger = logging.getLogger(__name__)


class ReconcileAgent:
    """Stage 6 - Reconciliation: matches routed instruction against settlement records."""

    async def run(self, state: InstructionState) -> InstructionState:
        logger.debug("Running %s for instruction_id=%s", self.__class__.__name__, state.instruction_id)
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
            logger.info(
                "Reconciliation matched: instruction_id=%s amount=%s",
                state.instruction_id,
                amount,
            )
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
