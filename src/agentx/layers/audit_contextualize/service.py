import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from agentx.db.repositories.metrics_repo import EvidenceRepository
from agentx.db.schema import EvidenceEventRow
from agentx.domain.models import InstructionState, JourneyState


class AuditContextualizeService:
    def __init__(self, session: AsyncSession):
        self.evidence = EvidenceRepository(session)

    async def log(self, state: InstructionState, stage: int, stage_label: str, action: str, detail: str, actor: str = "ai") -> None:
        await self.evidence.add(EvidenceEventRow(
            id=f"EVD-{uuid.uuid4().hex[:8].upper()}",
            instruction_id=state.instruction_id,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            stage=stage,
            stage_label=stage_label,
            event_type=action,
            summary=detail,
            actor=actor,
        ))

    async def record_block(self, state: InstructionState, block: str) -> InstructionState:
        labels = {
            "ingest": (1, "Ingestion", "ingestion"),
            "transaction_processing": (3, "Validate & Enrich", "validation"),
            "repair": (4, "Repair + Templatise", "repair"),
            "route": (5, "Routing", "routing"),
            "reconcile": (6, "Reconciliation", "reconciliation"),
        }
        stage, label, action = labels.get(block, (1, "Processing", "update"))
        await self.log(state, stage, label, action, f"{block} completed for {state.instruction_id}")
        return state
