"""
MediAgent — Execution Graph

Builds the LangGraph StateGraph. The Supervisor is the only node with
conditional routing logic — every other agent always returns control
to the Supervisor when it finishes. This is what allows different
requests to produce completely different execution paths instead of
a fixed pipeline.
"""

from langgraph.graph import StateGraph, END

from backend.workflow.state import WorkflowState
from backend.agents.supervisor import supervisor_node, route_from_supervisor
from backend.agents.medical_agent import medical_agent_node
from backend.agents.records_agent import records_agent_node
from backend.agents.appointment_agent import appointment_agent_node
from backend.agents.knowledge_agent import knowledge_agent_node
from backend.agents.pharmacy_agent import pharmacy_agent_node
from backend.agents.navigation_agent import navigation_agent_node
from backend.agents.safety_agent import safety_agent_node


def build_graph():
    graph = StateGraph(WorkflowState)

    # --- Register nodes ---
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("medical_agent", medical_agent_node)
    graph.add_node("records_agent", records_agent_node)
    graph.add_node("appointment_agent", appointment_agent_node)
    graph.add_node("knowledge_agent", knowledge_agent_node)
    graph.add_node("medication_agent", pharmacy_agent_node)
    graph.add_node("navigation_agent", navigation_agent_node)
    graph.add_node("safety_agent", safety_agent_node)

    graph.set_entry_point("supervisor")

    # --- Supervisor decides the next node dynamically ---
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "medical_agent": "medical_agent",
            "records_agent": "records_agent",
            "appointment_agent": "appointment_agent",
            "knowledge_agent": "knowledge_agent",
            "medication_agent": "medication_agent",
            "navigation_agent": "navigation_agent",
            "safety_agent": "safety_agent",
            "end": END,
        },
    )

    # --- Every agent returns control to the Supervisor ---
    for agent in [
        "medical_agent",
        "records_agent",
        "appointment_agent",
        "knowledge_agent",
        "medication_agent",
        "navigation_agent",
    ]:
        graph.add_edge(agent, "supervisor")

    # Safety Agent always runs last and terminates the workflow
    graph.add_edge("safety_agent", END)

    return graph.compile()


# Compiled, importable graph instance
mediagent_graph = build_graph()