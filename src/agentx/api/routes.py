import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from agentx.api.serializers import (
    exception_summary,
    instruction_detail,
    instruction_summary,
    workbench_card,
)
from agentx.api.ws_manager import ws_manager
from agentx.config import settings
from agentx.db.engine import get_session
from agentx.db.repositories.instruction_repo import InstructionRepository, WorkbenchRepository
from agentx.db.repositories.metrics_repo import ConfigRepository, EvidenceRepository
from agentx.layers.analytics.service import AnalyticsService
from agentx.layers.ingest.idp_schema import append_timeline, normalize_golden_schema
from agentx.layers.ops_assistant.agent import OpsAssistantAgent
from agentx.layers.orchestrator.graph import build_graph
from agentx.workers.pipeline_runner import PipelineRunner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

_graph = None


async def _broadcast_instruction_event(
    session: AsyncSession,
    instruction_id: str,
    event_type: str = "instruction_updated",
    *,
    workbench_id: str | None = None,
) -> None:
    inst_repo = InstructionRepository(session)
    row = await inst_repo.get(instruction_id)
    if not row:
        return

    workbench_row = None
    if workbench_id:
        workbench_row = await WorkbenchRepository(session).get(workbench_id)
    else:
        workbench_row = await WorkbenchRepository(session).get_by_ref(instruction_id)

    payload: dict[str, Any] = {
        "type": event_type,
        "id": instruction_id,
        "instruction": instruction_summary(row),
    }
    if workbench_row:
        payload["workbench"] = workbench_card(workbench_row, row)
    if row.is_exception:
        payload["exception"] = exception_summary(row)
    await ws_manager.broadcast(payload)


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


class StageUpdate(BaseModel):
    stage: str


class CommentBody(BaseModel):
    user: str
    text: str
    time: str


class ApproveBody(BaseModel):
    fields: dict[str, str] | None = None
    note: str | None = None


class FieldsUpdateBody(BaseModel):
    fields: dict[str, str]
    note: str | None = None


class ChatBody(BaseModel):
    message: str


@router.get("/me")
async def get_me():
    return {"display_name": settings.default_user}


@router.get("/dashboard/kpis")
async def dashboard_kpis(session: AsyncSession = Depends(get_session)):
    svc = AnalyticsService(session)
    return await svc.get_kpis()


@router.get("/dashboard/journey-health")
async def dashboard_journey(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_journey_health()


@router.get("/dashboard/ops-metrics")
async def dashboard_ops_metrics(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_ops_metrics()


@router.get("/dashboard/attention")
async def dashboard_attention(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_attention()


@router.get("/dashboard/channels")
async def dashboard_channels(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_channels()


@router.get("/dashboard/routing")
async def dashboard_routing(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_routing()


@router.get("/dashboard/intents")
async def dashboard_intents(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_intents()


@router.get("/instructions")
async def list_instructions(session: AsyncSession = Depends(get_session)):
    rows = await InstructionRepository(session).list_queue()
    return [instruction_summary(r) for r in rows]


@router.get("/exceptions")
async def list_exceptions(session: AsyncSession = Depends(get_session)):
    rows = await InstructionRepository(session).list_exceptions()
    return [exception_summary(r) for r in rows]


@router.get("/instructions/{instruction_id}")
async def get_instruction(instruction_id: str, session: AsyncSession = Depends(get_session)):
    row = await InstructionRepository(session).get(instruction_id)
    if not row:
        raise HTTPException(404, "Instruction not found")
    return instruction_detail(row)


@router.patch("/instructions/{instruction_id}/fields")
async def update_instruction_fields(
    instruction_id: str,
    body: FieldsUpdateBody,
    session: AsyncSession = Depends(get_session),
):
    if not body.fields:
        raise HTTPException(400, "No field corrections provided")

    repo = InstructionRepository(session)
    row = await repo.get(instruction_id)
    if not row:
        raise HTTPException(404, "Instruction not found")

    golden = dict(row.golden_schema or {})
    golden.update(body.fields)

    decisions = list(row.decisions or [])
    decisions.append(f"Human corrections saved: {', '.join(body.fields.keys())}")

    timeline = list(row.timeline or [])
    append_timeline(timeline, "Reviewer saved field corrections")
    if body.note:
        timeline.append(body.note)

    updated = await repo.update(
        instruction_id,
        golden_schema=normalize_golden_schema(golden),
        decisions=decisions,
        timeline=timeline,
    )
    await _broadcast_instruction_event(session, instruction_id)
    return instruction_detail(updated)


@router.post("/instructions/{instruction_id}/approve")
async def approve_instruction(instruction_id: str, body: ApproveBody, session: AsyncSession = Depends(get_session)):
    logger.info("Approve requested: instruction_id=%s note=%s", instruction_id, body.note or "(none)")
    repo = InstructionRepository(session)
    row = await repo.get(instruction_id)
    if not row:
        logger.warning("Approve failed — instruction not found: %s", instruction_id)
        raise HTTPException(404, "Instruction not found")
    wb = await WorkbenchRepository(session).get_by_ref(instruction_id)
    if wb:
        wb.stage = "approved"
        await session.commit()
        logger.info("Workbench stage set to approved: instruction_id=%s request_id=%s", instruction_id, wb.id)

    runner = PipelineRunner(get_graph(), session)
    result = await runner.resume_after_approval(
        instruction_id,
        fields=body.fields,
        note=body.note,
        broadcast=ws_manager.broadcast,
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Resume failed"))

    await _broadcast_instruction_event(session, instruction_id)
    return {
        "ok": True,
        "ref": instruction_id,
        "message": f"{instruction_id} approved — routed and reconciled",
        "status": result.get("status"),
    }


@router.get("/workbench/requests")
async def list_workbench(session: AsyncSession = Depends(get_session)):
    rows = await WorkbenchRepository(session).list_all()
    inst_repo = InstructionRepository(session)
    cards = []
    for row in rows:
        instruction = await inst_repo.get(row.ref)
        cards.append(workbench_card(row, instruction))
    return cards


@router.get("/workbench/requests/{request_id}")
async def get_workbench(request_id: str, session: AsyncSession = Depends(get_session)):
    row = await WorkbenchRepository(session).get(request_id)
    if not row:
        raise HTTPException(404, "Request not found")
    instruction = await InstructionRepository(session).get(row.ref)
    return workbench_card(row, instruction)


@router.patch("/workbench/requests/{request_id}/stage")
async def update_stage(request_id: str, body: StageUpdate, session: AsyncSession = Depends(get_session)):
    row = await WorkbenchRepository(session).update_stage(request_id, body.stage)
    if not row:
        raise HTTPException(404, "Request not found")
    await _broadcast_instruction_event(session, row.ref, workbench_id=request_id)
    instruction = await InstructionRepository(session).get(row.ref)
    return workbench_card(row, instruction)


@router.post("/workbench/requests/{request_id}/comments")
async def add_comment(request_id: str, body: CommentBody, session: AsyncSession = Depends(get_session)):
    row = await WorkbenchRepository(session).add_comment(request_id, body.model_dump())
    if not row:
        raise HTTPException(404, "Request not found")
    instruction = await InstructionRepository(session).get(row.ref)
    return workbench_card(row, instruction)


@router.get("/workbench/insights")
async def workbench_insights(session: AsyncSession = Depends(get_session)):
    return await AnalyticsService(session).get_workbench_insights()


@router.get("/audit")
async def audit_trail(session: AsyncSession = Depends(get_session)):
    events = await EvidenceRepository(session).list_all()
    return [
        {
            "id": e.id,
            "instruction_id": e.instruction_id,
            "timestamp": e.timestamp.isoformat(),
            "stage": e.stage,
            "stage_label": e.stage_label,
            "summary": e.summary,
            "detail": e.detail,
            "actor": e.actor,
        }
        for e in events
    ]


@router.get("/config/rules")
async def config_rules(session: AsyncSession = Depends(get_session)):
    return await ConfigRepository(session).get_rules()


@router.get("/assistant/welcome")
async def assistant_welcome(session: AsyncSession = Depends(get_session)):
    stats = await AnalyticsService(session).get_welcome_stats()
    return {"greeting": f"Good morning, {settings.default_user}", "stats": stats}


@router.post("/assistant/chat")
async def assistant_chat(body: ChatBody, session: AsyncSession = Depends(get_session)):
    agent = OpsAssistantAgent(session)
    result = await agent.chat(body.message)

    async def stream():
        yield {"event": "message", "data": result["reply_html"]}
        if result.get("meta"):
            yield {"event": "meta", "data": str(result["meta"])}

    return EventSourceResponse(stream())


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    source_type: str = Form("api"),
    session: AsyncSession = Depends(get_session),
):
    filename = file.filename or ""
    logger.info("API ingest request: filename=%s source_type=%s", filename or "(unnamed)", source_type)
    raw = await file.read()
    runner = PipelineRunner(get_graph(), session)
    result = await runner.run(raw, source_type, filename, broadcast=ws_manager.broadcast)
    if result.get("success"):
        logger.info(
            "API ingest complete: instruction_id=%s status=%s needs_human_review=%s",
            result.get("instruction_id"),
            result.get("status"),
            result.get("needs_human_review"),
        )
    else:
        logger.error("API ingest failed: filename=%s error=%s", filename, result.get("error"))
    return result


@router.websocket("/ws/ops")
async def websocket_ops(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
