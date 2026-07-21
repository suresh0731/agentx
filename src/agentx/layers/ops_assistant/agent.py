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
            at_risk = insights["sla_at_risk"]
            reply = (
                f'SLA compliance is at <strong class="text-emerald-400">{sla}%</strong>, '
                f"above your <strong>99.0%</strong> target. "
                f'You have <strong class="text-amber-400">{at_risk} instructions</strong> at risk '
                f"in the next 2 hours — I'd recommend prioritising those in the Exceptions queue."
            )
            stats = [f"{sla}% compliance", f"{at_risk} at risk"]
        elif "recon" in msg or "reconciliation" in msg:
            rollups = await self.analytics.metrics.get("metric_rollups") or {}
            rate = rollups.get("reconciliation_match_rate", 99.2)
            exc = rollups.get("recon_exceptions", 8)
            reply = (
                f'Reconciliation match rate is <strong class="text-emerald-400">{rate}%</strong>. '
                f'There are <strong class="text-red-400">{exc} open exceptions</strong> — '
                f"settlement amount mismatches and missing confirmations. Shall I list the instruction IDs?"
            )
            stats = [f"{exc} recon exceptions", f"{rate}% match rate"]
        elif "exception" in msg or "priority" in msg:
            att = await self.analytics.get_attention()
            total = att.get("total", 47)
            high = att.get("high_priority", 12)
            reply = (
                f'You have <strong class="text-amber-400">{total} items</strong> in the Exception Queue. '
                f'<strong class="text-red-400">{high} are high priority</strong> — '
                f"low-confidence, AML holds, and repair failures. I can open the highest-priority item for review."
            )
            stats = [f"{high} high priority", f"{total} in queue"]
        elif "bottleneck" in msg or "stage" in msg:
            jh = await self.analytics.get_journey_health()
            bottleneck = next((s for s in jh.get("stages", []) if s.get("is_bottleneck")), None)
            if bottleneck:
                rate = bottleneck["pass_rate"]
                label = bottleneck["label"]
                reply = (
                    f'Stage <strong>{bottleneck["stage"]} — {label}</strong> is the main bottleneck at '
                    f'<strong class="text-amber-400">{rate}%</strong>. '
                    f"The top issue is quantity mapping ambiguity, primarily from Email + PDF instructions."
                )
                stats = [f"{rate}% pass rate", "Email + PDF"]
            else:
                reply = (
                    'Stage <strong>4 — Repair + Templatise</strong> is the main bottleneck at '
                    '<strong class="text-amber-400">94.2%</strong>. '
                    "The top issue is quantity mapping ambiguity, primarily from Email + PDF instructions."
                )
                stats = ["94.2% pass rate", "Email + PDF"]
        elif "swift" in msg:
            channels = await self.analytics.get_channels()
            swift = next((c for c in channels if c["name"] == "SWIFT"), {})
            volume = swift.get("volume", 1284)
            stp = swift.get("stp_rate", 98.2)
            if "valid" in msg:
                reply = (
                    '<strong class="text-amber-400">12 SWIFT instructions</strong> failed validation today — '
                    "duplicate detection flags and missing ISIN. All have been routed to the Exception Queue."
                )
                stats = ["12 failed", "SWIFT channel"]
            else:
                reply = (
                    f"SWIFT channel: <strong>{volume}</strong> instructions today at "
                    f'<strong class="text-emerald-400">{stp}%</strong> STP.'
                )
                stats = [f"{stp}% STP"]
        else:
            rollups = await self.analytics.metrics.get("metric_rollups") or {}
            stp = rollups.get("overall_stp_rate", 96.8)
            exc = rollups.get("exception_queue_count", 47)
            reply = (
                f"Repair + Templatise is today's bottleneck at "
                f'<strong class="text-amber-400">94.2%</strong> pass rate. '
                f"Most issues relate to quantity mapping in the Email + PDF channel. "
                f'Overall STP is <strong class="text-emerald-400">{stp}%</strong> with '
                f'<strong class="text-amber-400">{exc} exceptions</strong> in queue.'
            )
            stats = ["31 below 98% confidence", "Stage 4 bottleneck"]
        return {"reply_html": reply, "meta": {"stats": stats}}
