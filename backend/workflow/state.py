"""
MediAgent — Shared Workflow State

This TypedDict is the single object passed between every node (agent)
in the LangGraph. Each agent reads what it needs and writes its own
output back, so the Supervisor can inspect results and decide the
next step (continue / stop / repeat / invoke another agent).
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict


AgentName = Literal[
    "supervisor",
    "medical_agent",
    "records_agent",
    "appointment_agent",
    "knowledge_agent",
    "safety_agent",
    "medication_agent",
    "navigation_agent",
    "report_analyzer",
    "navigation",
    "notification",
]


class WorkflowState(TypedDict, total=False):
    # --- Input ---
    patient_id: Optional[str]
    user_message: str
    uploaded_report_path: Optional[str]
    latitude: Optional[float]   # real patient coordinates, if ever wired up (e.g. browser geolocation)
    longitude: Optional[float]  # falls back to settings.DEFAULT_LATITUDE/LONGITUDE when absent

    # --- Supervisor control ---
    plan: List[AgentName]          # dynamically built execution plan
    history: List[AgentName]       # agents already executed, in order
    next_agent: Optional[AgentName]
    is_complete: bool
    requested_department: Optional[str]  # explicit specialist mention, e.g. "Dermatology"
    reasoning_trace: Optional[List[Dict[str, Any]]]  # ReAct Thought/Action steps from the LLM planner

    # --- Agent outputs (each agent writes its own key) ---
    medical_assessment: Optional[Dict[str, Any]]
    patient_records: Optional[Dict[str, Any]]
    appointment_result: Optional[Dict[str, Any]]
    knowledge_answer: Optional[Dict[str, Any]]
    safety_check: Optional[Dict[str, Any]]
    report_analysis: Optional[Dict[str, Any]]
    nearby_hospitals: Optional[List[Dict[str, Any]]]
    notification_status: Optional[Dict[str, Any]]
    patient_summary: Optional[Dict[str, Any]]
    medication_info: Optional[Dict[str, Any]]

    # --- Final output ---
    final_summary: Optional[str]
    emergency: bool