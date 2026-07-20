import asyncio

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.reconcile.agent import ReconcileAgent


class _MockReconClient:
    async def validate(self, instruction_id, destination, ingested_record, route_reference=None):
        return {
            "status": "matched",
            "matched": True,
            "summary": f"Reconciliation matched for {instruction_id} in {destination}.",
            "agent_output": (
                "Reconciliation Agent Report\n"
                "===========================\n"
                f"Instruction ID : {instruction_id}\n"
                "Result         : MATCHED"
            ),
            "external_reference": "SET-0001",
            "validated_at": "2026-07-20 12:00:00 UTC",
            "destination": destination,
            "counts": {"total": 3, "matched": 3, "mismatched": 0},
        }


def test_reconcile_agent_applies_successful_service_response():
    async def _run():
        state = InstructionState(
            instruction_id="INS-TEST-001",
            destination="RTAS",
            golden_schema={"transaction_type": "SUBSCRIPTION", "fund_code": "INF109K01VQ1"},
            decisions=["Routed to RTAS — ref RTAS-0001"],
            journey=JourneyState(completed_through=5, active_step=6),
            timeline=[],
        )

        return await ReconcileAgent(recon_client=_MockReconClient()).run(state)

    result = asyncio.run(_run())

    assert result.status == "Reconciled"
    assert result.recon_status == "matched"
    assert "Reconciliation Agent Report" in (result.recon_detail or "")
    assert result.journey.state == "completed"
    assert result.journey.completed_through == 6
    assert result.needs_human_review is False
