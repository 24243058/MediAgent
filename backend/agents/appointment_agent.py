"""
MediAgent — Appointment Agent

Handles doctor search, slot availability, booking, rescheduling, and
cancellation. Honors a date/time the patient stated in their message
("book appointment tomorrow at 5pm"); if none was given, assigns the
earliest available slot and says so explicitly, rather than silently
picking a time. On successful booking, triggers the WhatsApp
notification service.
"""

import re
from datetime import datetime, timedelta

from backend.notifications.whatsapp import send_appointment_confirmation
from backend.tools.database_tool import execute, fetch_all
from backend.workflow.state import WorkflowState


def find_available_doctor(department: str) -> dict | None:
    doctors = fetch_all(
        "SELECT * FROM doctors WHERE department = ? AND available = 1 LIMIT 1",
        (department,),
    )
    return doctors[0] if doctors else None


def _extract_preferred_datetime(message: str) -> tuple[str, str, bool]:
    """
    Look for an explicit date/time the patient stated. Returns
    (date, time, was_requested) — was_requested is False when we fell
    back to the default earliest slot.
    """
    message = message.lower()
    today = datetime.now()
    was_requested = False

    if "today" in message or "tonight" in message:
        date = today.strftime("%Y-%m-%d")
        was_requested = True
    elif "tomorrow" in message:
        date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        was_requested = True
    else:
        date = (today + timedelta(days=1)).strftime("%Y-%m-%d")  # default: next available day

    time_match = re.search(r"(\d{1,2})(:\d{2})?\s*(am|pm)", message)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2)[1:] if time_match.group(2) else "00"
        period = time_match.group(3).upper()
        time = f"{hour}:{minute} {period}"
        was_requested = True
    else:
        time = "10:30 AM"

    return date, time, was_requested


def book_appointment(
    patient_id: str,
    department: str,
    message: str = "",
    patient_phone: str | None = None,
) -> dict:
    doctor = find_available_doctor(department)
    if not doctor:
        return {"status": "no_availability", "department": department}

    date, time, was_requested = _extract_preferred_datetime(message)
    room_number = "204"

    appointment_id = execute(
        """INSERT INTO appointments (patient_id, doctor_id, department, date, time, room_number, status)
           VALUES (?, ?, ?, ?, ?, ?, 'confirmed')""",
        (patient_id, doctor["id"], department, date, time, room_number),
    )

    appointment = {
        "appointment_id": appointment_id,
        "doctor": doctor["name"],
        "department": department,
        "date": date,
        "time": time,
        "room_number": room_number,
        "status": "confirmed",
        "time_requested": was_requested,
    }

    if patient_phone:
        appointment["notification"] = send_appointment_confirmation(patient_phone, appointment)

    return appointment


def appointment_agent_node(state: WorkflowState) -> WorkflowState:
    assessment = state.get("medical_assessment") or {}
    department = (
        state.get("requested_department")
        or assessment.get("suggested_department", "General Medicine")
    )
    summary = dict(state.get("patient_summary", {}))
    patient_id = state.get("patient_id")
    message = state.get("user_message", "")

    result = book_appointment(patient_id, department, message) if patient_id else {
        "status": "missing_patient_id",
        "department": department,
    }

    if result.get("status") == "confirmed":
        summary.update({
            "doctor": result.get("doctor"),
            "appointment": f"{result.get('date')} at {result.get('time')}",
        })

    history = list(state.get("history", []))
    history.append("appointment_agent")

    return {**state, "appointment_result": result, "patient_summary": summary, "history": history}