from sqlalchemy.ext.asyncio import AsyncSession

from agentx.layers.analytics.service import AnalyticsService


class OpsAssistantAgent:
    def __init__(self, session: AsyncSession):
        self.analytics = AnalyticsService(session)

    async def chat(self, message: str) -> dict:
        msg = message.lower()
        stats: list[str] = []
        if "sla" in msg:
            rollups = await self.analytics.metrics.get("metric_rollups") or {}
            sla = rollups.get("sla_compliance", 99.4)
            insights = await self.analytics.get_workbench_insights()
            reply = f"SLA compliance is at <strong>{sla}%</strong> today. {insights['sla_at_risk']} instructions are at risk."
            stats = [f"{sla}% compliance", f"{insights['sla_at_risk']} at risk"]
        elif "recon" in msg or "reconciliation" in msg:
            rollups = await self.analytics.metrics.get("metric_rollups") or {}
            rate = rollups.get("reconciliation_match_rate", 99.2)
            exc = rollups.get("recon_exceptions", 8)
            reply = f"Reconciliation match rate is <strong>{rate}%</strong> with <strong>{exc}</strong> exceptions pending."
            stats = [f"{rate}% match", f"{exc} exceptions"]
        elif "exception" in msg or "priority" in msg:
            att = await self.analytics.get_attention()
            reply = f"There are <strong>{att.get('total', 47)}</strong> items requiring attention, including <strong>{att.get('high_priority', 12)}</strong> high priority."
            stats = [f"{att.get('total', 47)} total", f"{att.get('high_priority', 12)} high priority"]
        elif "bottleneck" in msg or "stage" in msg:
            jh = await self.analytics.get_journey_health()
            bottleneck = next((s for s in jh.get("stages", []) if s.get("is_bottleneck")), None)
            if bottleneck:
                reply = f"Stage <strong>{bottleneck['stage']} — {bottleneck['label']}</strong> is the main bottleneck at <strong>{bottleneck['pass_rate']}%</strong>."
                stats = [f"{bottleneck['pass_rate']}% pass rate"]
            else:
                reply = "Repair + Templatise is the main bottleneck at <strong>94.2%</strong>."
                stats = ["94.2% pass rate"]
        elif "swift" in msg:
            channels = await self.analytics.get_channels()
            swift = next((c for c in channels if c["name"] == "SWIFT"), {})
            reply = f"SWIFT channel: <strong>{swift.get('volume', 1284)}</strong> instructions today at <strong>{swift.get('stp_rate', 98.2)}%</strong> STP."
            stats = [f"{swift.get('stp_rate', 98.2)}% STP"]
        else:
            rollups = await self.analytics.metrics.get("metric_rollups") or {}
            reply = f"Overall STP is <strong>{rollups.get('overall_stp_rate', 96.8)}%</strong> with <strong>{rollups.get('exception_queue_count', 47)}</strong> exceptions in queue."
            stats = [f"{rollups.get('overall_stp_rate', 96.8)}% STP", f"{rollups.get('exception_queue_count', 47)} exceptions"]
        return {"reply_html": reply, "meta": {"stats": stats}}
