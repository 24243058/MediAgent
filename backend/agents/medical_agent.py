"""
MediAgent — Medical Agent

Performs symptom assessment and suggests risk level, department, and
tests. Also explains abnormal values from an uploaded report when
present. Never produces an official diagnosis.
"""

from backend.tools.llm import call_llm
from backend.workflow.state import WorkflowState

SYSTEM_PROMPT = """You are the Medical Agent in MediAgent, a hospital
care coordination system. Given a patient's message (and optional lab
report values), provide:
- risk_level: low | medium | high | emergency
- suggested_department
- suggested_tests: list
- home_care_advice
Never give an official diagnosis — always recommend consulting a doctor
for confirmation. Respond in structured form."""


# Very small demo keyword map — replace with real call_llm(SYSTEM_PROMPT, message) parsing
CONDITION_GUESSES = [
    (["fever", "chills", "body ache"], "Possible Viral Fever", "medium"),
    (["cough", "cold", "sore throat", "throat"], "Possible Upper Respiratory Infection", "low"),
    (["breath", "chest pain", "dizzy"], "Possible Cardiac/Respiratory Concern", "high"),
    (["vomit", "infection", "headache"], "Possible Viral Infection", "medium"),
]


def _guess_condition(message: str) -> tuple[str, str]:
    """Return (condition_label, risk_level) based on simple keyword matching."""
    for keywords, condition, risk in CONDITION_GUESSES:
        if any(k in message for k in keywords):
            return condition, risk
    return "General Symptom Assessment", "low"


def medical_agent_node(state: WorkflowState) -> WorkflowState:
    message = state.get("user_message", "").lower()
    report = state.get("report_analysis")
    summary = dict(state.get("patient_summary", {}))

    condition, risk_level = _guess_condition(message)

    # TODO: replace with real call_llm(SYSTEM_PROMPT, message) parsing
    assessment = {
        "risk_level": risk_level,
        "suggested_department": "General Medicine",
        "suggested_tests": ["CBC", "Basic Metabolic Panel"],
        "home_care_advice": "Rest, stay hydrated, monitor symptoms.",
        "condition": condition,
        "based_on_report": bool(report),
    }

    summary.update({
        "risk_level": risk_level.title(),
        "department": assessment["suggested_department"],
        "condition": condition,
        "tests": assessment["suggested_tests"],
    })

    history = list(state.get("history", []))
    history.append("medical_agent")

    return {**state, "medical_assessment": assessment, "patient_summary": summary, "history": history}