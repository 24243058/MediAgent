"""
MediAgent — Records Agent

Retrieves the patient's EHR: previous visits, allergies, medical
history, prescriptions, and past appointments from SQLite.
"""

from backend.tools.database_tool import fetch_all, fetch_one
from backend.workflow.state import WorkflowState


def get_patient_record(patient_id: str) -> dict:
    patient = fetch_one("SELECT * FROM patients WHERE id = ?", (patient_id,))
    if not patient:
        return {}

    return {
        "profile": patient,
        "visits": fetch_all("SELECT * FROM visits WHERE patient_id = ? ORDER BY visit_date DESC", (patient_id,)),
        "prescriptions": fetch_all("SELECT * FROM prescriptions WHERE patient_id = ?", (patient_id,)),
        "lab_reports": fetch_all("SELECT * FROM lab_reports WHERE patient_id = ?", (patient_id,)),
        "appointments": fetch_all("SELECT * FROM appointments WHERE patient_id = ? ORDER BY date DESC", (patient_id,)),
    }


def records_agent_node(state: WorkflowState) -> WorkflowState:
    patient_id = state.get("patient_id")
    records = get_patient_record(patient_id) if patient_id else {}

    history = list(state.get("history", []))
    history.append("records_agent")

    return {**state, "patient_records": records, "history": history}
