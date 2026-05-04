from langgraph.graph import END, StateGraph

from app.modules.agents.aggregator_agent import aggregator_node
from app.modules.agents.docs_agent import docs_node
from app.modules.agents.quality_agent import quality_node
from app.modules.agents.security_agent import security_node
from app.modules.agents.orchestrator import orchestrator_node
from app.modules.agents.tests_agent import tests_node
from app.core.state import AgentState

SPECIALIST_AGENTS = ["security", "quality", "tests", "docs"]


def build_graph():
    workflow = StateGraph(AgentState)

    # ── nodes ──────────────────────────────────────────────────────────────
    workflow.add_node("supervisor",  orchestrator_node)
    workflow.add_node("security",    security_node)
    workflow.add_node("quality",     quality_node)
    workflow.add_node("tests",       tests_node)
    workflow.add_node("docs",        docs_node)
    workflow.add_node("aggregator",  aggregator_node)

    # ── entry point ────────────────────────────────────────────────────────
    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "security":   "security",
            "quality":    "quality",
            "tests":      "tests",
            "docs":       "docs",
            "aggregator": "aggregator",
            "FINISH":     END,
        },
    )

    for agent in SPECIALIST_AGENTS:
        workflow.add_edge(agent, "supervisor")

    workflow.add_edge("aggregator", END)

    return workflow.compile()


pr_reviewer_graph = build_graph()