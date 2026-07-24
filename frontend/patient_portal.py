"""
MediAgent — Patient Portal

Streamlit UI: chat transcript occupies ~70% of the screen. The right
panel is a single "focus card" that switches based on what actually
happened in the workflow — Medical Summary, Emergency, Appointment,
Medication, Nearby Hospitals, or Knowledge — rather than stacking every
possible card at once. The Agent Timeline and report upload stay
available underneath regardless of the current focus.

Run with: streamlit run frontend/patient_portal.py
"""

from urllib.parse import quote
import sys
from pathlib import Path

import requests
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

API_BASE = "http://localhost:8000/api"

st.set_page_config(page_title="MediAgent — Patient Portal", page_icon="🏥", layout="wide")


def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


local_css("frontend/styles.css")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_state" not in st.session_state:
    st.session_state.last_state = {}
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "last_report_name" not in st.session_state:
    st.session_state.last_report_name = None
if "focus_panel" not in st.session_state:
    st.session_state.focus_panel = "idle"


def load_patients():
    """Pull the seeded patient list so the chat has a real patient_id to book against."""
    try:
        from backend.tools.database_tool import fetch_all
        return fetch_all("SELECT id, name FROM patients ORDER BY id")
    except Exception as e:
        st.session_state.patient_load_error = str(e)
        return []


patients = load_patients()

# ---------------- Branded header ----------------
header_left, header_right = st.columns([3, 1])
with header_left:
    st.markdown(
        """
        <div class="mg-app-header">
            <div>
                <p class="mg-title">🏥 MediAgent</p>
                <p class="mg-tagline">AI Hospital Care Coordination Platform</p>
            </div>
            <div class="mg-status-pill">🟢 Demo Mode</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with header_right:
    if patients:
        options = {f"{p['name']}": p["id"] for p in patients}
        selected_name = st.selectbox("Patient profile", list(options.keys()), label_visibility="visible")
        st.session_state.patient_id = str(options[selected_name])
    else:
        error = st.session_state.get("patient_load_error")
        if error:
            st.error(f"Couldn't load patients: {error}")
        else:
            st.warning("No patients found — run `python -m backend.database.seed`.")
        st.session_state.patient_id = None

RISK_COLOR = {"low": "green", "medium": "yellow", "high": "orange", "emergency": "red", "critical": "red"}
RISK_EMOJI = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}

STEP_META = {
    "medical_agent": ("🩺", "Medical Agent", "Symptoms assessed"),
    "records_agent": ("📂", "Records Agent", "History retrieved"),
    "appointment_agent": ("📅", "Appointment Agent", "Slot booked"),
    "knowledge_agent": ("📚", "Knowledge Agent", "Guidance retrieved"),
    "medication_agent": ("💊", "Medication Agent", "Medicine info retrieved"),
    "navigation_agent": ("📍", "Navigation Agent", "Nearby hospitals found"),
    "safety_agent": ("🛡", "Safety Agent", "Validation complete"),
}


def _focus_panel_for(state: dict) -> str:
    """
    Derive which single focus card to show, based on what the workflow
    actually did this turn — not on re-scanning the raw message. This
    keeps the panel truthful to execution, matching the Agent Timeline.
    """
    history = state.get("history", [])
    if state.get("emergency"):
        return "emergency"
    if "appointment_agent" in history and (state.get("appointment_result") or {}).get("status") == "confirmed":
        return "appointment"
    if "medication_agent" in history:
        return "medication"
    if "navigation_agent" in history:
        return "maps"
    if "knowledge_agent" in history:
        return "knowledge"
    if "medical_agent" in history:
        return "medical"
    return "idle"


chat_col, side_col = st.columns([7, 3])

# ==================== LEFT: Chat (≈70%) ====================
with chat_col:
    st.markdown("#### 💬 Talk to MediAgent")

    for role, text in st.session_state.chat_history:
        avatar = "👤" if role == "user" else "🤖"
        label = "You" if role == "user" else "MediAgent"
        st.markdown(
            f"""
            <div class="chat-row {role}">
                <div class="chat-avatar">{avatar}</div>
                <div class="chat-bubble-wrap {role}">
                    <div class="chat-label">{label}</div>
                    <div class="chat-bubble {role}">{text}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    user_input = st.chat_input("Describe your symptoms, ask about medicine, or book an appointment...")
    if user_input:
        st.session_state.chat_history.append(("user", user_input))

        with st.spinner("Coordinating your care..."):
            try:
                response = requests.post(
                    f"{API_BASE}/chat",
                    json={"patient_id": st.session_state.get("patient_id"), "message": user_input},
                    timeout=60,
                )
                result = response.json()
            except Exception as e:
                result = {"final_summary": f"Error contacting MediAgent backend: {e}"}

        st.session_state.last_state = result
        st.session_state.focus_panel = _focus_panel_for(result)
        summary_text = result.get("final_summary") or "MediAgent processed your request — see the summary panel."
        st.session_state.chat_history.append(("assistant", summary_text))
        st.rerun()

# ==================== RIGHT: Focus panel (≈30%) ====================
with side_col:
    state = st.session_state.last_state
    panel = st.session_state.focus_panel
    summary = state.get("patient_summary") or {}
    assessment = state.get("medical_assessment") or {}

    st.markdown('<div class="card">', unsafe_allow_html=True)

    # ---- Emergency ----
    if panel == "emergency":
        st.markdown('<div class="focus-label">🚨 Emergency</div>', unsafe_allow_html=True)
        hospitals = state.get("nearby_hospitals", [])
        top = hospitals[0] if hospitals else None
        st.markdown('<div class="emergency-nav-card">', unsafe_allow_html=True)
        st.markdown('<div class="title">🚑 Nearest Emergency Hospital</div>', unsafe_allow_html=True)
        if top:
            maps_url = f"https://www.google.com/maps/search/{quote(top['name'])}"
            st.markdown(
                f"""
                <div class="hospital-name">{top['name']}</div>
                <div class="meta">📍 {top['distance_km']} km &nbsp;·&nbsp; 🕒 {top['eta_minutes']} min</div>
                <a class="maps-btn" href="{maps_url}" target="_blank">Open Google Maps</a>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.write("No hospital data available.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("📍 Demo data — not connected to your real location or Google Maps.")

    # ---- Appointment ----
    elif panel == "appointment":
        st.markdown('<div class="focus-label">📅 Appointment</div>', unsafe_allow_html=True)
        appointment = state.get("appointment_result", {})
        timing_note = (
            "✔ Booked for your requested time"
            if appointment.get("time_requested")
            else "ℹ️ Earliest available slot — ask for a different time if needed"
        )
        st.markdown(
            f"""
            <div class="booking-card">
                <div class="doctor">{appointment.get('doctor')}</div>
                <div class="dept">{appointment.get('department')}</div>
                <div class="row">🗓 {appointment.get('date')} &nbsp;·&nbsp; 🕓 {appointment.get('time')}</div>
                <div class="row">🚪 Room {appointment.get('room_number')}</div>
                <span class="confirmed-badge">✔ Confirmed</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(timing_note)
        st.caption("This appointment is now live on the Hospital Dashboard.")

    # ---- Medication ----
    elif panel == "medication":
        st.markdown('<div class="focus-label">💊 Medication</div>', unsafe_allow_html=True)
        med = state.get("medication_info", {})
        if med.get("drug"):
            otc_class = "otc" if med.get("otc") else "rx"
            otc_label = "Over-the-counter" if med.get("otc") else "Prescription only"
            st.markdown(
                f"""
                <div class="medication-card">
                    <div class="drug-name">{med['drug']}</div>
                    <div class="category">{med.get('category', '-')}</div>
                    <div class="field-label">Common Use</div>
                    <div class="field-value">{med.get('common_use', '-')}</div>
                    <span class="otc-badge {otc_class}">{otc_label}</span>
                    <div class="field-label">Note</div>
                    <div class="field-value">{med.get('note', '-')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.write(med.get("note", "No medication identified."))

    # ---- Nearby hospitals (non-emergency) ----
    elif panel == "maps":
        st.markdown('<div class="focus-label">📍 Nearby Hospitals</div>', unsafe_allow_html=True)
        st.markdown('<div class="maps-card">', unsafe_allow_html=True)
        st.markdown('<div class="title">Hospitals Near You</div>', unsafe_allow_html=True)
        for h in state.get("nearby_hospitals", []):
            maps_url = f"https://www.google.com/maps/search/{quote(h['name'])}"
            st.markdown(
                f"""
                <div class="hospital-row">
                    <div class="name">{h['name']}</div>
                    <div class="meta">📍 {h['distance_km']} km &nbsp;·&nbsp; 🕒 {h['eta_minutes']} min</div>
                    <a class="maps-btn" href="{maps_url}" target="_blank">Directions</a>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("📍 Demo data — not connected to your real location or Google Maps.")
    elif panel == "knowledge":
        st.markdown('<div class="focus-label">📚 Knowledge</div>', unsafe_allow_html=True)
        knowledge = state.get("knowledge_answer", {})
        sources = ", ".join(knowledge.get("sources", [])) or "-"
        st.markdown(
            f"""
            <div class="knowledge-card">
                <div class="answer">{knowledge.get('answer', 'No answer available.')}</div>
                <div class="sources">Sources: {sources}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---- Medical Summary (dashboard-style) ----
    elif panel == "medical":
        risk_raw = (summary.get("risk_level") or assessment.get("risk_level", "-")).lower()
        color = RISK_COLOR.get(risk_raw, "yellow")
        emoji = RISK_EMOJI.get(color, "🟡")
        condition = summary.get("condition", "-")
        department = summary.get("department", assessment.get("suggested_department", "-"))
        tests = summary.get("tests") or assessment.get("suggested_tests", [])
        tests_html = "".join(f'<span class="pill-tag">{t}</span>' for t in tests) or "-"
        st.markdown('<div class="focus-label">🩺 Medical Summary</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <p><span class="risk-badge {color}">{emoji} {risk_raw.title()} Risk</span></p>
            <p><b>Possible Condition</b><br>{condition}</p>
            <p><b>Department</b><br>{department}</p>
            <p><b>Recommended Tests</b><br>{tests_html}</p>
            """,
            unsafe_allow_html=True,
        )

    # ---- Report Analysis ----
    elif panel == "report":
        st.markdown('<div class="focus-label">📄 Report Analysis</div>', unsafe_allow_html=True)
        report = st.session_state.last_report or {}
        status_label = "⚠ Mild abnormalities" if report.get("has_abnormalities") else "✅ Normal"
        status_color = "#92400E" if report.get("has_abnormalities") else "#166534"
        st.markdown(
            f"""
            <div class="report-status-card">
                <div class="name">📄 {st.session_state.last_report_name}</div>
                <div class="status" style="color:{status_color}">{status_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for marker, v in report.get("values", {}).items():
            arrow = "↓" if v["status"] == "Low" else ("↑" if v["status"] == "High" else "→")
            status_class = v["status"].lower()
            st.markdown(
                f"""
                <div class="report-value-row">
                    <div class="marker">{marker}</div>
                    <div class="value">{v['value']} {v['unit']} {arrow}</div>
                    <div class="status-tag {status_class}">{v['status']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        for rec in report.get("recommendation", []):
            st.info(rec)

    # ---- Idle ----
    else:
        st.markdown(
            """
            <div class="idle-placeholder">
                <div class="big-icon">🩺</div>
                <p>Ask a question to get started — symptoms, a medicine, booking a specialist, or a nearby hospital.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Medical Reports (always available, compact) ----
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h4>📄 Medical Reports</h4>", unsafe_allow_html=True)

    if st.session_state.last_report:
        report = st.session_state.last_report
        status_label = "⚠ Mild abnormalities" if report.get("has_abnormalities") else "✅ Normal"
        status_color = "#92400E" if report.get("has_abnormalities") else "#166534"
        st.markdown(
            f"""
            <div class="report-status-card">
                <div class="name">📄 {st.session_state.last_report_name}</div>
                <div class="status" style="color:{status_color}">{status_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("View report details"):
            for marker, v in report.get("values", {}).items():
                arrow = "↓" if v["status"] == "Low" else ("↑" if v["status"] == "High" else "→")
                status_class = v["status"].lower()
                st.markdown(
                    f"""
                    <div class="report-value-row">
                        <div class="marker">{marker}</div>
                        <div class="value">{v['value']} {v['unit']} {arrow}</div>
                        <div class="status-tag {status_class}">{v['status']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            for rec in report.get("recommendation", []):
                st.info(rec)

    with st.expander("+ Upload Report"):
        uploaded = st.file_uploader(
            "Blood report, ECG, prescription, or PDF",
            type=["pdf", "png", "jpg", "jpeg"],
            key="main_report_upload",
            label_visibility="collapsed",
        )
        if uploaded and st.button("Analyze Report"):
            with st.spinner("Reading report..."):
                try:
                    files = {"file": (uploaded.name, uploaded.getvalue())}
                    resp = requests.post(f"{API_BASE}/reports/upload", files=files, timeout=60)
                    st.session_state.last_report = resp.json()
                    st.session_state.last_report_name = uploaded.name
                    st.session_state.focus_panel = "report"
                    st.rerun()
                except Exception as e:
                    st.error(f"Report analysis failed: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ---- Supervisor Reasoning (only shown when the LLM ReAct planner actually ran) ----
    trace = [t for t in (state.get("reasoning_trace") or []) if t.get("mode") == "llm"]
    if trace:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("<h4>🧠 Supervisor Reasoning (live LLM)</h4>", unsafe_allow_html=True)
        for i, step in enumerate(trace, 1):
            st.markdown(f"**Step {i} — action: `{step.get('action')}`**")
            st.caption(step.get("thought", ""))
        st.markdown("</div>", unsafe_allow_html=True)

    # ---- Agent Timeline (dynamic — only agents that actually ran) ----
    executed = [s for s in state.get("history", []) if s != "supervisor"]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("<h4>🤖 Agent Timeline</h4>", unsafe_allow_html=True)

    if not executed:
        st.caption("No agents have run yet — send a message to get started.")
    else:
        st.markdown('<div class="agent-timeline">', unsafe_allow_html=True)

        # Supervisor always "runs" first conceptually
        st.markdown(
            """
            <div class="agent-step">
                <div class="icon">🧠</div>
                <div class="body">
                    <div class="agent-name">Supervisor</div>
                    <div class="agent-status">✔ Planning complete</div>
                </div>
            </div>
            <div class="agent-connector">↓</div>
            """,
            unsafe_allow_html=True,
        )

        for i, step in enumerate(executed):
            icon, name, status = STEP_META.get(step, ("⚙️", step.replace("_", " ").title(), "Complete"))
            st.markdown(
                f"""
                <div class="agent-step">
                    <div class="icon">{icon}</div>
                    <div class="body">
                        <div class="agent-name">{name}</div>
                        <div class="agent-status">✔ {status}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if i < len(executed) - 1:
                st.markdown('<div class="agent-connector">↓</div>', unsafe_allow_html=True)

        if state.get("is_complete"):
            st.markdown(
                """
                <div class="agent-connector">↓</div>
                <div class="agent-step">
                    <div class="icon">✅</div>
                    <div class="body">
                        <div class="agent-name">Response Ready</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)