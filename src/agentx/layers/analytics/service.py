from sqlalchemy.ext.asyncio import AsyncSession

from agentx.layers.analytics.ops_metrics import build_ops_metrics
from agentx.db.repositories.instruction_repo import InstructionRepository, WorkbenchRepository
from agentx.db.repositories.metrics_repo import MetricRepository
from agentx.db.schema import WorkbenchRequestRow


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.metrics = MetricRepository(session)
        self.instructions = InstructionRepository(session)
        self.workbench = WorkbenchRepository(session)

    async def get_kpis(self) -> dict:
        rollups = await self.metrics.get("metric_rollups")
        return {
            "primary": rollups.get("primary", []),
            "secondary": rollups.get("secondary", []),
        }

    async def get_journey_health(self) -> dict:
        return await self.metrics.get("journey_health") or {}

    async def get_ops_metrics(self) -> dict:
        rollups = await self.metrics.get("metric_rollups") or {}
        return {"metrics": build_ops_metrics(rollups)}

    async def get_attention(self) -> dict:
        return await self.metrics.get("attention") or {}

    async def get_channels(self) -> list:
        return await self.metrics.get("channels") or []

    async def get_routing(self) -> dict:
        return await self.metrics.get("routing") or {}

    async def get_intents(self) -> list:
        return await self.metrics.get("intents") or []

    async def get_workbench_insights(self) -> dict:
        cards = await self.workbench.list_all()
        total = len(cards)
        in_review = sum(1 for c in cards if c.stage == "review")
        at_risk = sum(1 for c in cards if 0 < c.sla_remaining <= 15)
        breached = sum(1 for c in cards if c.sla_remaining <= 0)
        avg_conf = sum(c.confidence for c in cards if c.confidence > 0) / max(1, sum(1 for c in cards if c.confidence > 0))
        distribution = {}
        for c in cards:
            distribution[c.stage] = distribution.get(c.stage, 0) + 1
        return {
            "total": total,
            "in_review": in_review,
            "sla_at_risk": at_risk,
            "sla_breached": breached,
            "avg_confidence": round(avg_conf, 1),
            "distribution": distribution,
            "paths_today": {"auto_approved": 18, "human_approved": 12, "rejected": 3, "escalated": 2},
        }

    async def get_welcome_stats(self) -> list:
        rollups = await self.metrics.get("metric_rollups") or {}
        return [
            {"label": "STP Rate", "value": f"{rollups.get('overall_stp_rate', 96.8)}%"},
            {"label": "Exceptions", "value": str(rollups.get("exception_queue_count", 47))},
            {"label": "SLA", "value": f"{rollups.get('sla_compliance', 99.4)}%"},
        ]
