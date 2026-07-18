from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentx.db.schema import InstructionRow, WorkbenchRequestRow


class InstructionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[InstructionRow]:
        result = await self.session.execute(select(InstructionRow).order_by(InstructionRow.instruction_id))
        return list(result.scalars().all())

    async def list_queue(self) -> list[InstructionRow]:
        result = await self.session.execute(
            select(InstructionRow).where(InstructionRow.in_queue.is_(True)).order_by(InstructionRow.instruction_id)
        )
        return list(result.scalars().all())

    async def list_exceptions(self) -> list[InstructionRow]:
        result = await self.session.execute(
            select(InstructionRow).where(InstructionRow.is_exception.is_(True)).order_by(InstructionRow.instruction_id)
        )
        return list(result.scalars().all())

    async def get(self, instruction_id: str) -> InstructionRow | None:
        return await self.session.get(InstructionRow, instruction_id)

    async def save(self, row: InstructionRow) -> InstructionRow:
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def update(self, instruction_id: str, **kwargs) -> InstructionRow | None:
        row = await self.get(instruction_id)
        if not row:
            return None
        for k, v in kwargs.items():
            setattr(row, k, v)
        await self.session.commit()
        await self.session.refresh(row)
        return row


class WorkbenchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[WorkbenchRequestRow]:
        result = await self.session.execute(select(WorkbenchRequestRow).order_by(WorkbenchRequestRow.id))
        return list(result.scalars().all())

    async def get(self, request_id: str) -> WorkbenchRequestRow | None:
        return await self.session.get(WorkbenchRequestRow, request_id)

    async def get_by_ref(self, ref: str) -> WorkbenchRequestRow | None:
        result = await self.session.execute(select(WorkbenchRequestRow).where(WorkbenchRequestRow.ref == ref))
        return result.scalar_one_or_none()

    async def update_stage(self, request_id: str, stage: str) -> WorkbenchRequestRow | None:
        row = await self.get(request_id)
        if not row:
            return None
        row.stage = stage
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def add_comment(self, request_id: str, comment: dict) -> WorkbenchRequestRow | None:
        row = await self.get(request_id)
        if not row:
            return None
        comments = list(row.comments or [])
        comments.append(comment)
        row.comments = comments
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def save(self, row: WorkbenchRequestRow) -> WorkbenchRequestRow:
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row
