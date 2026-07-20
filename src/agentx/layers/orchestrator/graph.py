import logging
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agentx.domain.models import InstructionState
from agentx.layers.ingest.agent import IngestAgent
from agentx.layers.reconcile.agent import ReconcileAgent
from agentx.layers.route.agent import RouteAgent
from agentx.layers.transaction_processing.agent import TransactionProcessingAgent

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    instruction: dict
    needs_human_review: bool
    approved: bool


ingest_agent = IngestAgent()
txn_agent = TransactionProcessingAgent()
route_agent = RouteAgent()
reconcile_agent = ReconcileAgent()
checkpointer = MemorySaver()


def _instruction_id(state: GraphState) -> str:
    return (state.get("instruction") or {}).get("instruction_id", "unknown")


def _node_result(result: InstructionState, state: GraphState) -> GraphState:
    return {
        "instruction": result.model_dump(),
        "needs_human_review": result.needs_human_review,
        "approved": state.get("approved", False),
    }


async def ingest_node(state: GraphState) -> GraphState:
    raw = state["instruction"].get("_raw", b"")
    source_type = state["instruction"].get("source_type", "api")
    filename = state["instruction"].get("filename", "")
    logger.info("Graph node ingest: filename=%s source_type=%s", filename or "(unnamed)", source_type)
    pre_id = state["instruction"].get("instruction_id")
    result = await ingest_agent.run(raw, source_type, filename, instruction_id=pre_id)
    logger.info(
        "Graph node ingest complete: instruction_id=%s parser=%s",
        result.instruction_id,
        result.intake_json.get("parser_used"),
    )
    return {"instruction": result.model_dump(), "needs_human_review": False, "approved": False}


async def detect_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node detect: instruction_id=%s", inst.instruction_id)
    result = await txn_agent.detect(inst)
    logger.info(
        "Graph node detect complete: instruction_id=%s intent=%s journey_step=%s",
        result.instruction_id,
        result.intent,
        result.journey.completed_through,
    )
    return _node_result(result, state)


async def validate_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node validate: instruction_id=%s", inst.instruction_id)
    result = await txn_agent.validate(inst)
    logger.info(
        "Graph node validate complete: instruction_id=%s needs_review=%s held_step=%s",
        result.instruction_id,
        result.needs_human_review,
        result.journey.held_step,
    )
    return _node_result(result, state)


async def repair_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node repair: instruction_id=%s", inst.instruction_id)
    result = await txn_agent.repair(inst)
    logger.info(
        "Graph node repair complete: instruction_id=%s confidence=%.1f needs_review=%s risk=%s",
        result.instruction_id,
        result.overall_confidence,
        result.needs_human_review,
        result.risk_label,
    )
    return _node_result(result, state)


async def route_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node route: instruction_id=%s", inst.instruction_id)
    result = await route_agent.run(inst)
    logger.info(
        "Graph node route complete: instruction_id=%s destination=%s status=%s",
        result.instruction_id,
        result.destination,
        result.status,
    )
    return _node_result(result, state)


async def reconcile_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node reconcile: instruction_id=%s destination=%s", inst.instruction_id, inst.destination)
    result = await reconcile_agent.run(inst)
    logger.info(
        "Graph node reconcile complete: instruction_id=%s status=%s needs_review=%s",
        result.instruction_id,
        result.status,
        result.needs_human_review,
    )
    return _node_result(result, state)


async def human_review_node(state: GraphState) -> GraphState:
    logger.info("Graph node human_review: instruction_id=%s (passthrough)", _instruction_id(state))
    return state


def route_after_validate(state: GraphState) -> str:
    inst = InstructionState.model_validate(state["instruction"])
    if inst.needs_human_review and inst.journey.held_step == 3 and not state.get("approved"):
        logger.info("Routing after validate -> human_review: instruction_id=%s", _instruction_id(state))
        return "human_review"
    logger.info("Routing after validate -> repair: instruction_id=%s", _instruction_id(state))
    return "repair"


def route_after_repair(state: GraphState) -> str:
    if state.get("needs_human_review") and not state.get("approved"):
        logger.info("Routing after repair -> human_review: instruction_id=%s", _instruction_id(state))
        return "human_review"
    logger.info("Routing after repair -> route: instruction_id=%s", _instruction_id(state))
    return "route"


def route_after_human(state: GraphState) -> str:
    if state.get("approved"):
        logger.info("Routing after human_review -> route: instruction_id=%s", _instruction_id(state))
        return "route"
    logger.info("Routing after human_review -> END: instruction_id=%s", _instruction_id(state))
    return END


def route_after_reconcile(state: GraphState) -> str:
    inst = InstructionState.model_validate(state["instruction"])
    if inst.needs_human_review and not state.get("approved"):
        logger.info("Routing after reconcile -> human_review: instruction_id=%s", inst.instruction_id)
        return "human_review"
    logger.info("Routing after reconcile -> END: instruction_id=%s status=%s", inst.instruction_id, inst.status)
    return END


def build_graph():
    logger.info(
        "Building LangGraph pipeline (ingest -> detect -> validate -> repair -> route -> reconcile)"
    )
    g = StateGraph(GraphState)
    g.add_node("ingest", ingest_node)
    g.add_node("detect", detect_node)
    g.add_node("validate", validate_node)
    g.add_node("repair", repair_node)
    g.add_node("human_review", human_review_node)
    g.add_node("route", route_node)
    g.add_node("reconcile", reconcile_node)
    g.set_entry_point("ingest")
    g.add_edge("ingest", "detect")
    g.add_edge("detect", "validate")
    g.add_conditional_edges(
        "validate",
        route_after_validate,
        {"human_review": "human_review", "repair": "repair"},
    )
    g.add_conditional_edges(
        "repair",
        route_after_repair,
        {"human_review": "human_review", "route": "route"},
    )
    g.add_conditional_edges(
        "human_review",
        route_after_human,
        {"route": "route", END: END},
    )
    g.add_edge("route", "reconcile")
    g.add_conditional_edges(
        "reconcile",
        route_after_reconcile,
        {"human_review": "human_review", END: END},
    )
    return g.compile(checkpointer=checkpointer)
