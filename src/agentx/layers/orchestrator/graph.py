import logging
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agentx.domain.models import InstructionState
from agentx.layers.ingest.agent import IngestAgent
from agentx.layers.route_reconcile.agent import RouteReconcileAgent
from agentx.layers.transaction_processing.agent import TransactionProcessingAgent

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    instruction: dict
    needs_human_review: bool
    approved: bool


ingest_agent = IngestAgent()
txn_agent = TransactionProcessingAgent()
route_agent = RouteReconcileAgent()
checkpointer = MemorySaver()


def _instruction_id(state: GraphState) -> str:
    return (state.get("instruction") or {}).get("instruction_id", "unknown")


async def ingest_node(state: GraphState) -> GraphState:
    raw = state["instruction"].get("_raw", b"")
    source_type = state["instruction"].get("source_type", "api")
    filename = state["instruction"].get("filename", "")
    logger.info("Graph node ingest: filename=%s source_type=%s", filename or "(unnamed)", source_type)
    pre_id = state["instruction"].get("instruction_id")
    result = await ingest_agent.run(raw, source_type, filename, instruction_id=pre_id)
    logger.info("Graph node ingest complete: instruction_id=%s parser=%s",
                result.instruction_id, result.intake_json.get("parser_used"))
    return {"instruction": result.model_dump(), "needs_human_review": False, "approved": False}


async def transaction_processing_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node transaction_processing: instruction_id=%s", inst.instruction_id)
    result = await txn_agent.run(inst)
    logger.info(
        "Graph node transaction_processing complete: instruction_id=%s intent=%s confidence=%.1f needs_review=%s risk=%s",
        result.instruction_id,
        result.intent,
        result.overall_confidence,
        result.needs_human_review,
        result.risk_label,
    )
    return {
        "instruction": result.model_dump(),
        "needs_human_review": result.needs_human_review,
        "approved": state.get("approved", False),
    }


async def route_reconcile_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    logger.info("Graph node route_reconcile: instruction_id=%s destination=%s", inst.instruction_id, inst.destination)
    result = await route_agent.run(inst)
    logger.info(
        "Graph node route_reconcile complete: instruction_id=%s status=%s needs_review=%s",
        result.instruction_id,
        result.status,
        result.needs_human_review,
    )
    return {
        "instruction": result.model_dump(),
        "needs_human_review": result.needs_human_review,
        "approved": state.get("approved", False),
    }


async def human_review_node(state: GraphState) -> GraphState:
    logger.info("Graph node human_review: instruction_id=%s (passthrough)", _instruction_id(state))
    return state


def route_after_txn(state: GraphState) -> str:
    if state.get("needs_human_review") and not state.get("approved"):
        logger.info("Routing after transaction_processing -> human_review: instruction_id=%s", _instruction_id(state))
        return "human_review"
    logger.info("Routing after transaction_processing -> route_reconcile: instruction_id=%s", _instruction_id(state))
    return "route_reconcile"


def route_after_human(state: GraphState) -> str:
    if state.get("approved"):
        logger.info("Routing after human_review -> route_reconcile: instruction_id=%s", _instruction_id(state))
        return "route_reconcile"
    logger.info("Routing after human_review -> END: instruction_id=%s", _instruction_id(state))
    return END


def route_after_reconcile(state: GraphState) -> str:
    inst = InstructionState.model_validate(state["instruction"])
    if inst.needs_human_review and not state.get("approved"):
        logger.info("Routing after route_reconcile -> human_review: instruction_id=%s", inst.instruction_id)
        return "human_review"
    logger.info("Routing after route_reconcile -> END: instruction_id=%s status=%s", inst.instruction_id, inst.status)
    return END


def build_graph():
    logger.info("Building LangGraph pipeline (ingest -> transaction_processing -> route_reconcile)")
    g = StateGraph(GraphState)
    g.add_node("ingest", ingest_node)
    g.add_node("transaction_processing", transaction_processing_node)
    g.add_node("human_review", human_review_node)
    g.add_node("route_reconcile", route_reconcile_node)
    g.set_entry_point("ingest")
    g.add_edge("ingest", "transaction_processing")
    g.add_conditional_edges("transaction_processing", route_after_txn, {"human_review": "human_review", "route_reconcile": "route_reconcile"})
    g.add_conditional_edges("human_review", route_after_human, {"route_reconcile": "route_reconcile", END: END})
    g.add_conditional_edges("route_reconcile", route_after_reconcile, {"human_review": "human_review", END: END})
    return g.compile(checkpointer=checkpointer)
