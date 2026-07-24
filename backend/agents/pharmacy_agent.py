"""
MediAgent — Medication / Pharmacy Agent

Answers general medicine questions ("Can I take paracetamol?", "What is
ibuprofen for?") using a small demo reference table. Gives general
orientation only — category, common use, OTC/prescription status — and
never confirms a specific dosage. Always defers to a pharmacist or
doctor for anything beyond that. The Safety Agent still validates the
response afterward, but medication questions are answered here, not by
Safety, since Safety isn't equipped to reason about drug information.
"""

from backend.workflow.state import WorkflowState

# Demo reference table — replace with a real drug database / RAG lookup.
MEDICATION_INFO = {
    "paracetamol": {"category": "Pain reliever / fever reducer", "common_use": "Mild-to-moderate pain, headache, and fever.", "otc": True},
    "acetaminophen": {"category": "Pain reliever / fever reducer", "common_use": "Mild-to-moderate pain, headache, and fever.", "otc": True},
    "ibuprofen": {"category": "NSAID (anti-inflammatory)", "common_use": "Pain, inflammation, and fever.", "otc": True},
    "aspirin": {"category": "NSAID / blood thinner", "common_use": "Pain, fever, and (at low dose) cardiovascular prevention.", "otc": True},
    "amoxicillin": {"category": "Antibiotic", "common_use": "Bacterial infections — requires a prescription and a completed course.", "otc": False},
    "cetirizine": {"category": "Antihistamine", "common_use": "Allergy symptoms such as sneezing and itching.", "otc": True},
    "omeprazole": {"category": "Proton pump inhibitor", "common_use": "Acid reflux and heartburn.", "otc": True},
}


def _lookup_medication(message: str) -> tuple[str | None, dict | None]:
    for name, info in MEDICATION_INFO.items():
        if name in message:
            return name, info
    return None, None


def pharmacy_agent_node(state: WorkflowState) -> WorkflowState:
    message = state.get("user_message", "").lower()
    name, info = _lookup_medication(message)

    if info:
        medication_info = {
            "drug": name.title(),
            "category": info["category"],
            "common_use": info["common_use"],
            "otc": info["otc"],
            "note": (
                "General information only — follow package directions and "
                "consult a pharmacist or doctor for dosing specific to your "
                "age, weight, and health conditions."
            ),
        }
    else:
        medication_info = {
            "drug": None,
            "note": (
                "I couldn't identify a specific medicine in your question. "
                "Please name the medicine, or consult a pharmacist directly."
            ),
        }

    summary = dict(state.get("patient_summary", {}))
    if medication_info.get("drug"):
        summary["medication"] = medication_info["drug"]

    history = list(state.get("history", []))
    history.append("medication_agent")

    return {**state, "medication_info": medication_info, "patient_summary": summary, "history": history}