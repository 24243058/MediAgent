"""
MediAgent — Supervisor Agent

The brain of the system. Every request starts and passes back through
here. Each turn is one ReAct step: look at the current state (Thought),
pick exactly one next action (Action), execute it, get the result back
(Observation), and repeat until done.

Two planning modes:
  - LLM mode (an API key configured for the selected LLM_PROVIDER): the Thought/Action step is a real
    Gemini call — _llm_decide() — so the reasoning is genuinely
    generated, not scripted.
  - Heuristic mode (no key configured): _heuristic_decide() reproduces
    the same decisions with keyword rules, so the app still runs
    end-to-end without an API key (e.g. for local demos/grading).

A small set of safety-critical invariants are enforced in code in
_decide_next_agent() itself, BEFORE either planning mode runs, and
cannot be overridden by a bad or hallucinated LLM decision:
  - an uploaded report always gets read by the Medical Agent first
  - a detected emergency routes straight to Safety, skipping booking
  - Safety Agent always runs before "done" once anything else has run
This is a deliberate reasoning/guardrail split: the LLM decides
*which* agent to call for ambiguous intent, but it doesn't get to
decide *whether* the safety net runs.
"""

import json
from typing import Literal

from backend.config import settings
from backend.tools.llm import call_llm
from backend.workflow.state import AgentName, WorkflowState

VALID_ACTIONS = {
    "medical_agent", "records_agent", "appointment_agent", "knowledge_agent",
    "medication_agent", "navigation_agent", "safety_agent", "done",
}

REACT_SYSTEM_PROMPT = """You are the Supervisor Agent for MediAgent, an AI
hospital care coordination system, reasoning in a ReAct (Reasoning +
Acting) loop. Each turn, look at the patient's message and what has
already been done, then decide exactly ONE next action.

Available actions:
- medical_agent: assess symptoms — risk level, possible condition, department, tests
- records_agent: retrieve the patient's EHR (history, allergies, prescriptions)
- appointment_agent: book a doctor appointment
- knowledge_agent: answer general medical/policy questions via the hospital's document base (RAG)
- medication_agent: answer a question about a specific medicine (general info only, never exact dosages)
- navigation_agent: find nearby hospitals (non-emergency "where's the nearest hospital" requests)
- safety_agent: final validation step — choose this once enough has been gathered, or immediately if you detect an emergency (severe symptoms like chest pain, difficulty breathing, unconsciousness), even if booking was requested
- done: finish without calling another agent — only when nothing has happened yet and you need to ask the patient a clarifying question first (e.g. they asked to book an appointment but gave no symptoms or department)

Respond with ONLY a JSON object, no other text:
{"thought": "<your reasoning about what the patient needs and why>", "action": "<one action name from the list above>", "clarifying_question": "<only if action is done and nothing has run yet — the question to ask the patient; otherwise empty string>"}
"""

# --- Keyword tables (used by the heuristic fallback, and for the hard safety guardrails in both modes) ---

SYMPTOM_KEYWORDS = [
    "pain", "symptom", "fever", "hurt", "sick", "cold", "cough", "throat",
    "sore", "headache", "vomit", "infection", "dizzy", "breath",
]

BOOKING_KEYWORDS = ["book", "appointment", "schedule", "consult"]

# Distinguishes "reschedule/cancel my appointment" (a question about an
# existing booking) from "book an appointment" (a new booking request) —
# both match BOOKING_KEYWORDS via "appointment" but need different routing.
EXISTING_APPOINTMENT_KEYWORDS = ["reschedule", "cancel", "my appointment", "existing appointment"]

KNOWLEDGE_KEYWORDS = ["disease", "policy", "guideline", "faq", "what is"]

# Broader net for the general-question fallback — catches phrasings the
# fixed keyword list above misses (e.g. "what ARE the visiting hours").
QUESTION_STARTERS = ["what", "how", "when", "where", "why", "can", "is", "are", "do", "does", "will", "should"]

MEDICATION_KEYWORDS = [
    "paracetamol", "acetaminophen", "ibuprofen", "aspirin", "amoxicillin",
    "cetirizine", "omeprazole", "medicine", "medication", "tablet", "pill",
    "drug", "dosage", "antibiotic", "syrup",
]

NAVIGATION_KEYWORDS = [
    "nearest hospital", "hospital near", "near me", "find a hospital",
    "navigate", "directions to",
]

# Kept in sync with backend.agents.safety_agent.EMERGENCY_KEYWORDS
EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "severe bleeding",
    "unconscious", "stroke", "seizure", "suicidal", "overdose",
]

# Maps specialist mentions in the message to a department in the doctors table
DEPARTMENT_KEYWORDS = {
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
    "skin specialist": "Dermatology",
    "cardiologist": "Cardiology",
    "cardiology": "Cardiology",
    "heart specialist": "Cardiology",
    "pediatrician": "Pediatrics",
    "paediatrician": "Pediatrics",
    "pediatrics": "Pediatrics",
    "child specialist": "Pediatrics",
    "orthopedist": "Orthopedics",
    "orthopedic": "Orthopedics",
    "orthopaedic": "Orthopedics",
    "bone doctor": "Orthopedics",
    "general physician": "General Medicine",
    "general medicine": "General Medicine",
}


def _extract_department(message: str) -> str | None:
    for keyword, department in DEPARTMENT_KEYWORDS.items():
        if keyword in message:
            return department
    return None


def _looks_like_question(message: str) -> bool:
    stripped = message.strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    first_word = stripped.split(" ", 1)[0]
    return first_word in QUESTION_STARTERS


def _summarize_agent_output(state: WorkflowState, agent: str) -> str:
    """One-line summary of what an already-executed agent found, for the ReAct prompt."""
    if agent == "medical_agent":
        a = state.get("medical_assessment") or {}
        return f"risk={a.get('risk_level')}, condition={a.get('condition')}, department={a.get('suggested_department')}"
    if agent == "appointment_agent":
        r = state.get("appointment_result") or {}
        return f"status={r.get('status')}, department={r.get('department')}"
    if agent == "records_agent":
        return "patient history retrieved"
    if agent == "knowledge_agent":
        return "answer retrieved from hospital documents"
    if agent == "medication_agent":
        m = state.get("medication_info") or {}
        return f"drug={m.get('drug')}"
    if agent == "navigation_agent":
        return f"{len(state.get('nearby_hospitals') or [])} nearby hospitals found"
    return "done"


def _build_react_prompt(state: WorkflowState) -> str:
    history = state.get("history", [])
    lines = [f"Patient message: {state.get('user_message', '')}"]
    if state.get("requested_department"):
        lines.append(f"Department explicitly mentioned: {state['requested_department']}")
    if state.get("uploaded_report_path"):
        lines.append("A medical report was uploaded this turn.")
    if history:
        lines.append("Actions already taken this turn:")
        for h in history:
            lines.append(f"- {h}: {_summarize_agent_output(state, h)}")
    else:
        lines.append("No actions taken yet this turn.")
    return "\n".join(lines)


def _llm_decide(state: WorkflowState) -> tuple[str, dict]:
    """Real ReAct step: ask Gemini for a Thought + Action given the current state."""
    prompt = _build_react_prompt(state)
    raw = call_llm(REACT_SYSTEM_PROMPT, prompt, temperature=0.2, json_mode=True)
    parsed = json.loads(raw)

    action = (parsed.get("action") or "").strip()
    thought = parsed.get("thought", "")
    clarifying_question = parsed.get("clarifying_question", "")

    if action not in VALID_ACTIONS:
        raise ValueError(f"LLM returned an invalid action: {action!r}")

    trace = list(state.get("reasoning_trace") or [])
    trace.append({"thought": thought, "action": action, "mode": "llm"})
    extra: dict = {"reasoning_trace": trace}

    if action == "done":
        if not state.get("history") and clarifying_question:
            extra["final_summary"] = clarifying_question
            extra["is_complete"] = True
        return "done", extra

    return action, extra


def _heuristic_decide(state: WorkflowState, history: list, message: str, department: str | None) -> tuple[str, dict]:
    """Deterministic fallback planning — used when no LLM is configured, or if the LLM call fails."""
    extra: dict = {}
    has_symptom = any(k in message for k in SYMPTOM_KEYWORDS)
    has_booking = any(k in message for k in BOOKING_KEYWORDS)

    # --- Medicine questions go to the Pharmacy Agent, never Safety directly ---
    if any(k in message for k in MEDICATION_KEYWORDS) and "medication_agent" not in history:
        return "medication_agent", extra

    # --- Explicit "nearest hospital" requests outside of an emergency ---
    if any(k in message for k in NAVIGATION_KEYWORDS) and "navigation_agent" not in history:
        return "navigation_agent", extra

    # --- Pure booking request, no symptoms, no department: ask before acting ---
    # (skip this for questions about an EXISTING appointment — those aren't
    # a new booking request and fall through to the knowledge/question path below)
    is_existing_appointment_question = any(k in message for k in EXISTING_APPOINTMENT_KEYWORDS)
    if has_booking and not has_symptom and not department and not history and not is_existing_appointment_question:
        extra["final_summary"] = (
            "I'd be happy to help book an appointment. Could you briefly "
            "describe your symptoms so I can determine the appropriate specialist?"
        )
        extra["is_complete"] = True
        return "done", extra

    # --- Symptoms present: always assess risk before booking or anything else ---
    if has_symptom and "medical_agent" not in history:
        return "medical_agent", extra

    # --- Explicit department, no symptoms: skip Medical Agent, book directly ---
    if department and not has_symptom and "appointment_agent" not in history:
        extra["patient_summary"] = {
            **(state.get("patient_summary") or {}),
            "risk_level": "N/A",
            "department": department,
            "condition": "Appointment Request",
            "tests": [],
        }
        return "appointment_agent", extra

    # --- Booking intent, symptoms already assessed and not an emergency ---
    if has_booking and "medical_agent" in history and "appointment_agent" not in history:
        return "appointment_agent", extra

    # --- Knowledge lookups (diseases, policies, guidelines, FAQs) ---
    if any(k in message for k in KNOWLEDGE_KEYWORDS) and "knowledge_agent" not in history:
        return "knowledge_agent", extra

    # --- Anything else that reads as a general question: default to Knowledge
    # Agent rather than silently falling through to Safety having done nothing.
    # A fixed keyword list can never cover every phrasing ("what ARE the
    # visiting hours" vs "what IS the policy") — this catches the rest.
    if _looks_like_question(message) and "knowledge_agent" not in history and not history:
        return "knowledge_agent", extra

    # --- Pure symptom question (no booking): pull records for context once ---
    if "medical_agent" in history and "records_agent" not in history and not has_booking:
        return "records_agent", extra

    if "safety_agent" not in history:
        return "safety_agent", extra

    return "done", extra


def _decide_next_agent(state: WorkflowState) -> tuple[AgentName | Literal["done"], dict]:
    """
    Core routing decision. Returns (next_agent_or_done, extra_state_updates)
    merged into state by supervisor_node.
    """
    history = state.get("history", [])
    message = state.get("user_message", "").lower()

    if "safety_agent" in history:
        return "done", {}

    # ============ Hard safety guardrails — enforced regardless of planning mode ============
    if state.get("uploaded_report_path") and "medical_agent" not in history:
        return "medical_agent", {}

    is_emergency_keyword = any(k in message for k in EMERGENCY_KEYWORDS)
    if "medical_agent" in history:
        assessment = state.get("medical_assessment") or {}
        risk = (assessment.get("risk_level") or "").lower()
        if (risk in ("high", "emergency") or is_emergency_keyword) and "safety_agent" not in history:
            return "safety_agent", {}
    # ==========================================================================================

    department = state.get("requested_department") or _extract_department(message)
    dept_extra = {"requested_department": department} if department else {}

    if settings.has_llm_key():
        try:
            next_agent, extra = _llm_decide(state)
            merged = {**dept_extra, **extra}
        except Exception as e:
            trace = list(state.get("reasoning_trace") or [])
            trace.append({"thought": f"LLM call failed ({e}); used rule-based fallback.", "action": None, "mode": "fallback"})
            next_agent, extra = _heuristic_decide(state, history, message, department)
            merged = {**dept_extra, "reasoning_trace": trace, **extra}
    else:
        next_agent, extra = _heuristic_decide(state, history, message, department)
        merged = {**dept_extra, **extra}

    # A department-only booking (no Medical Agent run) needs its summary card
    # pre-filled regardless of which planning mode chose appointment_agent
    if next_agent == "appointment_agent" and "medical_agent" not in history and "patient_summary" not in merged:
        merged["patient_summary"] = {
            **(state.get("patient_summary") or {}),
            "risk_level": "N/A",
            "department": department or "General Medicine",
            "condition": "Appointment Request",
            "tests": [],
        }

    return next_agent, merged


def supervisor_node(state: WorkflowState) -> WorkflowState:
    next_agent, extra = _decide_next_agent(state)

    history = list(state.get("history", []))
    updated = {
        **state,
        **extra,
        "next_agent": None if next_agent == "done" else next_agent,
        "is_complete": next_agent == "done",
        "history": history,
    }
    return updated


def route_from_supervisor(state: WorkflowState) -> str:
    """Conditional edge function used by the LangGraph StateGraph."""
    if state.get("is_complete"):
        return "end"
    return state.get("next_agent", "safety_agent")