"""
MediAgent — Navigation Agent

Handles explicit "nearest hospital" / "find a hospital near me" requests
that aren't tied to an emergency (the Safety Agent triggers the same
Navigation tool directly when it detects one). Kept as its own node so
the Supervisor can route to it independently and the frontend can show
a dedicated Maps card for this intent.
"""

from backend.config import settings
from backend.navigation.maps import find_nearby_hospitals
from backend.workflow.state import WorkflowState


def navigation_agent_node(state: WorkflowState) -> WorkflowState:
    hospitals = find_nearby_hospitals(
        state.get("latitude", settings.DEFAULT_LATITUDE),
        state.get("longitude", settings.DEFAULT_LONGITUDE),
    )

    history = list(state.get("history", []))
    history.append("navigation_agent")

    return {**state, "nearby_hospitals": hospitals, "history": history}