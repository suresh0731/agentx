from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agentx.domain.models import InstructionState
from agentx.layers.ingest.agent import IngestAgent
from agentx.layers.route_reconcile.agent import RouteReconcileAgent
from agentx.layers.transaction_processing.agent import TransactionProcessingAgent


class GraphState(TypedDict):
    instruction: dict
    needs_human_review: bool
    approved: bool


ingest_agent = IngestAgent()
txn_agent = TransactionProcessingAgent()
route_agent = RouteReconcileAgent()
checkpointer = MemorySaver()


async def ingest_node(state: GraphState) -> GraphState:
    raw = state["instruction"].get("_raw", b"")
    source_type = state["instruction"].get("source_type", "api")
    filename = state["instruction"].get("filename", "")
    result = await ingest_agent.run(raw, source_type, filename)
    return {"instruction": result.model_dump(), "needs_human_review": False, "approved": False}


async def transaction_processing_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    result = await txn_agent.run(inst)
    return {
        "instruction": result.model_dump(),
        "needs_human_review": result.needs_human_review,
        "approved": state.get("approved", False),
    }


async def route_reconcile_node(state: GraphState) -> GraphState:
    inst = InstructionState.model_validate(state["instruction"])
    result = await route_agent.run(inst)
    return {
        "instruction": result.model_dump(),
        "needs_human_review": result.needs_human_review,
        "approved": state.get("approved", False),
    }


async def human_review_node(state: GraphState) -> GraphState:
    return state


def route_after_txn(state: GraphState) -> str:
    if state.get("needs_human_review") and not state.get("approved"):
        return "human_review"
    return "route_reconcile"


def route_after_human(state: GraphState) -> str:
    if state.get("approved"):
        return "route_reconcile"
    return END


def route_after_reconcile(state: GraphState) -> str:
    inst = InstructionState.model_validate(state["instruction"])
    if inst.needs_human_review and not state.get("approved"):
        return "human_review"
    return END


def build_graph():
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
