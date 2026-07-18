import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from agentx.db.repositories.instruction_repo import InstructionRepository, WorkbenchRepository
from agentx.db.schema import InstructionRow, WorkbenchRequestRow


class PipelineRunner:
    def __init__(self, graph, session: AsyncSession):
        self.graph = graph
        self.session = session

    async def run(self, raw: bytes, source_type: str, filename: str) -> dict:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        initial = {
            "instruction": {"_raw": raw, "source_type": source_type, "filename": filename},
            "needs_human_review": False,
            "approved": False,
        }
        result = await self.graph.ainvoke(initial, config)
        inst = result["instruction"]
        instruction_id = inst["instruction_id"]

        inst_repo = InstructionRepository(self.session)
        await inst_repo.save(InstructionRow(
            instruction_id=instruction_id,
            intent=inst.get("intent"),
            channel=inst.get("channel"),
            routing_target=inst.get("destination"),
            confidence=inst.get("overall_confidence", 0),
            status=inst.get("status", "Processing"),
            journey=inst.get("journey", {}),
            golden_schema=inst.get("golden_schema"),
            intake_json=inst.get("intake_json"),
            party=(inst.get("intake_json") or {}).get("party", {}).get("name"),
            field_confidences=inst.get("field_confidences", {}),
            decisions=inst.get("decisions", []),
            repair_notes=inst.get("repair_notes", []),
            in_queue=True,
            is_exception=inst.get("needs_human_review", False),
            source_type=source_type,
            workbench_stage=inst.get("workbench_stage", "submitted"),
        ))

        if inst.get("needs_human_review"):
            wb_repo = WorkbenchRepository(self.session)
            req_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
            await wb_repo.save(WorkbenchRequestRow(
                id=req_id,
                ref=instruction_id,
                stage=inst.get("workbench_stage", "review"),
                intent=inst.get("intent") or "Unknown",
                source=inst.get("channel") or source_type,
                party=(inst.get("intake_json") or {}).get("party", {}).get("name", "Unknown"),
                amount=str((inst.get("golden_schema") or {}).get("amount", "—")),
                confidence=inst.get("overall_confidence", 0),
                journey=inst.get("journey", {}),
                fields=inst.get("field_confidences", {}),
                findings=inst.get("findings", []),
                explain=inst.get("explainability", ""),
            ))

        return {"instruction_id": instruction_id, "status": inst.get("status"), "needs_human_review": inst.get("needs_human_review")}
