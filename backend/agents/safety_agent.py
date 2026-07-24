"""
MediAgent — Safety Agent

Always executes last and can never be skipped. Detects emergencies,
can override unsafe responses from other agents, and recommends
immediate medical attention when warranted. On emergency detection,
triggers the Navigation tool to surface nearby hospitals.
"""

from backend.config import settings
from backend.navigation.maps import find_nearby_hospitals
from backend.workflow.state import WorkflowState

EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "severe bleeding",
    "unconscious", "stroke", "seizure", "suicidal", "overdose",
]


def _detect_emergency(state: WorkflowState) -> bool:
    message = state.get("user_message", "").lower()
    assessment = state.get("medical_assessment") or {}

    if any(kw in message for kw in EMERGENCY_KEYWORDS):
        return True
    if (assessment.get("risk_level") or "").lower() in ("high", "emergency"):
        return True
    return False


def _build_final_summary(state: WorkflowState, is_emergency: bool) -> str:
    """
    Turn whatever actually happened this turn into a plain-language
    chat response, so the patient is told the outcome directly instead
    of only seeing it in the side panel.
    """
    if is_emergency:
        hospitals = state.get("nearby_hospitals") or []
        if hospitals:
            top = hospitals[0]
            return (
                f"⚠️ This looks like it could be a medical emergency. Please seek immediate care. "
                f"The nearest emergency hospital is {top['name']}, about {top['distance_km']} km away "
                f"(~{top['eta_minutes']} min) — see the panel for directions."
            )
        return "⚠️ This looks like it could be a medical emergency. Please seek immediate medical attention."

    appointment = state.get("appointment_result")
    if appointment:
        if appointment.get("status") == "confirmed":
            timing_note = (
                "at your requested time"
                if appointment.get("time_requested")
                else "the earliest available slot — let me know if you'd like a different day or time"
            )
            return (
                f"You're booked with {appointment.get('doctor')} ({appointment.get('department')}) "
                f"on {appointment.get('date')} at {appointment.get('time')}, Room {appointment.get('room_number')} "
                f"— {timing_note}."
            )
        if appointment.get("status") == "no_availability":
            return (
                f"I wasn't able to find an available doctor in {appointment.get('department')} right now. "
                f"Please try again shortly or contact the front desk."
            )
        if appointment.get("status") == "missing_patient_id":
            return (
                "I can book that appointment, but I don't know which patient profile this is for. "
                "Please select a patient at the top of the page and send your request again."
            )
        return f"I wasn't able to complete that booking ({appointment.get('status', 'unknown issue')})."

    medication = state.get("medication_info")
    if medication is not None:
        if medication.get("drug"):
            return (
                f"{medication['drug']} is a {medication['category'].lower()}, typically used for "
                f"{medication['common_use'].lower()} {medication['note']}"
            )
        return medication.get("note", "I couldn't identify a specific medicine in your question.")

    knowledge = state.get("knowledge_answer")
    if knowledge:
        return knowledge.get("answer", "Here's what I found.")

    if state.get("nearby_hospitals") and not appointment:
        top = state["nearby_hospitals"][0]
        return (
            f"The nearest hospital is {top['name']}, about {top['distance_km']} km away "
            f"(~{top['eta_minutes']} min) — see the panel for directions."
        )

    assessment = state.get("medical_assessment")
    if assessment:
        tests = ", ".join(assessment.get("suggested_tests", [])) or "a basic checkup"
        return (
            f"Based on what you described, this could be {assessment.get('condition', 'a general concern').lower()}. "
            f"Risk level: {assessment.get('risk_level', '-').title()}. "
            f"I'd suggest {assessment.get('suggested_department', 'General Medicine')}, with tests such as {tests}. "
            f"{assessment.get('home_care_advice', '')}"
        ).strip()

    return "I've reviewed your request — let me know if you'd like more detail on anything above."


def safety_agent_node(state: WorkflowState) -> WorkflowState:
    is_emergency = _detect_emergency(state)
    summary = state.get("patient_summary", {})

    safety_check = {
        "emergency_detected": is_emergency,
        "recommendation": (
            "Seek immediate medical attention — nearest emergency hospitals below."
            if is_emergency
            else "No emergency indicators detected. Continue with the suggested plan."
        ),
    }

    updated = {**state, "safety_check": safety_check, "patient_summary": summary, "emergency": is_emergency}

    if is_emergency:
        updated["nearby_hospitals"] = find_nearby_hospitals(
            state.get("latitude", settings.DEFAULT_LATITUDE),
            state.get("longitude", settings.DEFAULT_LONGITUDE),
        )

    updated["final_summary"] = _build_final_summary(updated, is_emergency)

    history = list(state.get("history", []))
    history.append("safety_agent")
    updated["history"] = history
    updated["is_complete"] = True

    return updated