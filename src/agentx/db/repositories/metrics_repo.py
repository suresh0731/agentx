from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentx.db.schema import EvidenceEventRow, MetricRollupRow, ConfigRuleRow


class EvidenceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self, limit: int = 100) -> list[EvidenceEventRow]:
        result = await self.session.execute(
            select(EvidenceEventRow).order_by(EvidenceEventRow.timestamp.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, event: EvidenceEventRow) -> EvidenceEventRow:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event


class MetricRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> dict | None:
        row = await self.session.get(MetricRollupRow, key)
        return row.payload if row else None

    async def set(self, key: str, payload: dict) -> None:
        row = await self.session.get(MetricRollupRow, key)
        if row:
            row.payload = payload
        else:
            self.session.add(MetricRollupRow(key=key, payload=payload))
        await self.session.commit()


class ConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_rules(self) -> dict[str, list[str]]:
        result = await self.session.execute(select(ConfigRuleRow))
        return {row.category: row.rules for row in result.scalars().all()}
