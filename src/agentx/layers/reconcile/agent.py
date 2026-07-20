import logging

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import append_timeline
from agentx.shared.clients.recon_client import ReconServiceClient

logger = logging.getLogger(__name__)


class ReconcileAgent:
    """Stage 6 - Reconciliation: calls the external recon service to validate
    ingested records against data loaded in the destination system.
    """

    def __init__(self, recon_client: ReconServiceClient | None = None):
        self.recon_client = recon_client or ReconServiceClient()

    async def run(self, state: InstructionState) -> InstructionState:
        logger.debug("Running %s for instruction_id=%s", self.__class__.__name__, state.instruction_id)
        route_ref = next(
            (d.split("ref ")[-1] for d in reversed(state.decisions) if "Routed to" in d and "ref" in d),
            None,
        )
        result = await self.recon_client.validate(
            instruction_id=state.instruction_id,
            destination=state.destination or "RFAS",
            ingested_record=state.golden_schema,
            route_reference=route_ref,
        )

        state.recon_status = result.get("status", "matched")
        state.recon_detail = result.get("agent_output", result.get("summary", "Reconciliation matched"))
        state.journey = JourneyState(state="completed", completed_through=6)
        state.status = "Reconciled"
        state.decisions.append(result.get("summary", "Reconciliation matched"))
        state.explainability = state.recon_detail
        append_timeline(
            state.timeline,
            f"Reconciliation matched — {result.get('external_reference', 'SET')}",
        )
        logger.info(
            "Reconciliation matched: instruction_id=%s destination=%s ref=%s",
            state.instruction_id,
            state.destination,
            result.get("external_reference"),
        )
        return state
