import logging

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import append_timeline
from agentx.layers.route import rules_engine
from agentx.layers.route.output_writer import ensure_destination_folders, write_routing_output
from agentx.shared.mocks import external_apis as mocks

logger = logging.getLogger(__name__)


class RouteAgent:
    """Stage 5 - Routing: applies rule-based routing (via zen-engine) to
    decide the instruction's destination (RTAS/ViTAL/RFAS), writes the
    routing Excel output, and dispatches it.

    Routing rule:
        - intentHint in (subscription, redemption):
            - country in (HK, Hong Kong) -> RTAS
            - otherwise                 -> ViTAL
        - all other transaction types -> RFAS
    """

    DISPATCH = {
        "RTAS": mocks.dispatch_rtas,
        "ViTAL": mocks.dispatch_vital,
        "RFAS": mocks.dispatch_rfas,
    }

    async def run(self, state: InstructionState) -> InstructionState:
        logger.debug("Running %s for instruction_id=%s", self.__class__.__name__, state.instruction_id)
        ensure_destination_folders()
        txn = state.intake_json.get("transaction", {})
        intent_hint = txn.get("intentHint") or (state.intent or "").lower()
        country_field = state.golden_schema.get("country")
        country_from_schema = (
            country_field.get("value")
            if isinstance(country_field, dict)
            else country_field
        )
        country = txn.get("country") or country_from_schema
        dest = rules_engine.evaluate_destination(intent_hint, country)
        state.destination = dest
        logger.info("Routing instruction_id=%s to destination=%s", state.instruction_id, dest)

        output_path = write_routing_output(state, dest)
        state.decisions.append(f"Route output saved: {output_path.name}")

        result = await self.DISPATCH.get(dest, mocks.dispatch_rfas)(state.instruction_id)
        state.decisions.append(f"Routed to {dest} — ref {result['ref']}")
        state.journey = JourneyState(completed_through=5, active_step=6)
        append_timeline(state.timeline, f"Routed to {dest}")
        state.status = "Routed"
        logger.info(
            "[%s] routed to %s (ref=%s, output=%s)",
            state.instruction_id,
            dest,
            result["ref"],
            output_path,
        )
        return state
