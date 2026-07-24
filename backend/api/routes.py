"""
MediAgent — API Routes

Exposes the LangGraph workflow and supporting services (reports,
records, appointments) to the Streamlit frontends over HTTP.
"""

from unittest import result

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

from backend.reports.report_analyzer import analyze_report
from backend.workflow.graph import mediagent_graph
from backend.workflow.state import WorkflowState

router = APIRouter()


class ChatRequest(BaseModel):
    patient_id: str | None = None
    message: str


@router.post("/chat")
def chat(request: ChatRequest):
    """Run the full Supervisor-orchestrated agent workflow for one message."""
    initial_state: WorkflowState = {
        "patient_id": request.patient_id,
        "user_message": request.message,
        "history": [],
        "is_complete": False,
        "emergency": False,
        "patient_summary": {
            "risk_level": "Unknown",
            "department": "-",
            "condition": "-",
            "doctor": "-",
            "appointment": "-",
            "medication": "-",
            "report": "-",
            "nearest_hospital": "-",
            "notification": "-",
            "emergency": False,
        }
    }
    final_state = mediagent_graph.invoke(initial_state)
    print("FINAL STATE:")
    print(final_state)
    return final_state


@router.post("/reports/upload")
async def upload_report(file: UploadFile, patient_id: str | None = None):
    """Save an uploaded report and run it through the analyzer."""
    save_path = f"docs/sample_reports/{file.filename}"
    with open(save_path, "wb") as f:
        f.write(await file.read())

    analysis = analyze_report(save_path)
    return analysis


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "MediAgent"}
