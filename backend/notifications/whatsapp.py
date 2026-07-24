"""
MediAgent — WhatsApp Notification Service

Sends appointment confirmations (doctor details, hospital location,
reminder) after a successful booking. Runs in mock mode for the demo;
swap in the real Twilio WhatsApp API for production.
"""

from typing import Any, Dict

from backend.config import settings


def send_appointment_confirmation(patient_phone: str, appointment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send (or mock-send) a WhatsApp confirmation message.

    Returns a status dict consumed by the frontend's
    "WhatsApp Notification ✓ Sent" indicator.
    """
    message = (
        f"Appointment Confirmed ✅\n"
        f"Doctor: {appointment.get('doctor')}\n"
        f"Department: {appointment.get('department')}\n"
        f"Date: {appointment.get('date')} at {appointment.get('time')}\n"
        f"Room: {appointment.get('room_number')}\n"
        f"See you soon!"
    )

    if settings.USE_MOCK_WHATSAPP:
        return {
            "status": "sent",
            "mode": "mock",
            "to": patient_phone,
            "message": message,
        }

    # TODO: integrate real Twilio WhatsApp API using
    # settings.TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM
    raise NotImplementedError("Wire up the Twilio WhatsApp API call here.")
