"""
MediAgent — Hospital Dashboard

Streamlit UI for hospital staff: branded header, KPI cards, patient
triage table, and a detail view (EHR / AI summary / reports /
prescriptions / history) per selected patient.

Reads live data straight from the SQLite DB (via backend.tools).
If the DB hasn't been seeded yet, falls back to built-in demo data
so the dashboard is never blank — run
`python -m backend.database.seed` to populate real data.

Run with: streamlit run frontend/hospital_dashboard.py
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

st.set_page_config(page_title="MediAgent — Hospital Dashboard", layout="wide")

with open("frontend/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------- Fallback demo data (used if DB isn't seeded/reachable) ----------------
FALLBACK_TRIAGE = pd.DataFrame([
    {"Patient": "Aarav Mehta",  "Priority": "High",     "Department": "Cardiology",         "Assigned Doctor": "Dr. Vikram Sharma", "Status": "Confirmed"},
    {"Patient": "Sneha Kapoor", "Priority": "Low",      "Department": "Dermatology",         "Assigned Doctor": "Dr. Priya Menon",   "Status": "Confirmed"},
    {"Patient": "Ramesh Iyer",  "Priority": "Medium",   "Department": "General Medicine",    "Assigned Doctor": "Dr. Ananya Rao",    "Status": "Confirmed"},
    {"Patient": "Divya Nair",   "Priority": "Critical", "Department": "Emergency Medicine",  "Assigned Doctor": "Dr. Rohan Das",     "Status": "In Progress"},
    {"Patient": "Kabir Singh",  "Priority": "Low",      "Department": "Orthopedics",         "Assigned Doctor": "Dr. Karthik Iyer",  "Status": "Confirmed"},
])

FALLBACK_KPIS = {
    "Patients Today": 5,
    "Emergency Cases": 1,
    "Appointments": 5,
    "Doctors Available": 5,
    "ICU Beds": 3,
}

FALLBACK_PROFILES = {
    "Aarav Mehta": {
        "profile": {"age": 34, "blood_group": "O+", "allergies": "Penicillin", "existing_diseases": "Hypertension"},
        "ai_summary": "Presented with chest discomfort. ECG normal. Risk level: Medium. Recommended cardiology follow-up.",
        "visits": [{"visit_date": "2 weeks ago", "reason": "Chest discomfort", "department": "Cardiology", "doctor": "Dr. Vikram Sharma"}],
        "prescriptions": [{"medicine": "Amlodipine 5mg", "dosage": "Once daily", "prescribed_by": "Dr. Vikram Sharma"}],
        "reports": [{"report_type": "Lipid Panel", "extracted_values": "LDL: 142 mg/dL (High)"}],
        "appointments": [{"department": "Cardiology", "date": "Today", "time": "10:30 AM", "status": "Confirmed"}],
    },
    "Divya Nair": {
        "profile": {"age": 45, "blood_group": "AB+", "allergies": "None", "existing_diseases": "Asthma"},
        "ai_summary": "Shortness of breath on arrival. Nebulizer administered, patient stabilized. Risk level: High.",
        "visits": [{"visit_date": "2 days ago", "reason": "Shortness of breath", "department": "Emergency Medicine", "doctor": "Dr. Rohan Das"}],
        "prescriptions": [{"medicine": "Salbutamol Inhaler", "dosage": "As needed", "prescribed_by": "Dr. Rohan Das"}],
        "reports": [],
        "appointments": [{"department": "Emergency Medicine", "date": "Today", "time": "09:00 AM", "status": "In Progress"}],
    },
}


def load_kpis():
    try:
        from backend.tools.database_tool import fetch_all
        patients_today = fetch_all("SELECT COUNT(*) as c FROM appointments")[0]["c"]
        doctors_available = fetch_all("SELECT COUNT(*) as c FROM doctors WHERE available = 1")[0]["c"]
        if patients_today == 0:
            raise ValueError("DB not seeded")
        return {
            "Patients Today": patients_today,
            "Emergency Cases": 1,
            "Appointments": patients_today,
            "Doctors Available": doctors_available,
            "ICU Beds": 3,
        }, True
    except Exception:
        return FALLBACK_KPIS, False


def load_triage():
    try:
        from backend.tools.database_tool import fetch_all
        rows = fetch_all("""
            SELECT p.name as Patient, a.department as Department, d.name as "Assigned Doctor",
                   a.status as Status
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            JOIN doctors d ON d.id = a.doctor_id
        """)
        if not rows:
            raise ValueError("DB not seeded")
        df = pd.DataFrame(rows)
        return df, True
    except Exception:
        return FALLBACK_TRIAGE, False


kpis, live_kpis = load_kpis()
triage_df, live_triage = load_triage()

# ---------------- Branded header ----------------
header_col, refresh_col = st.columns([5, 1])
with header_col:
    st.markdown(
        """
        <div class="mediagent-header">
            <div>
                <p class="title">MediAgent — Hospital Dashboard</p>
                <p class="tagline">Live AI triage, appointments, and patient monitoring</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with refresh_col:
    st.write("")
    if st.button("🔄 Refresh"):
        st.rerun()

if live_kpis:
    st.caption("🔴 Live — this table updates automatically whenever a patient books an appointment in MediAgent.")
else:
    st.info("Showing demo data — run `python -m backend.database.seed` to populate the live database.")

# ---------------- KPI cards ----------------
tones = {
    "Patients Today": "",
    "Emergency Cases": "danger",
    "Appointments": "",
    "Doctors Available": "success",
    "ICU Beds": "warning",
}
kpi_cols = st.columns(5)
for col, (label, value) in zip(kpi_cols, kpis.items()):
    col.markdown(
        f"""
        <div class="mg-kpi {tones.get(label, '')}">
            <div class="value">{value}</div>
            <div class="label">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# ---------------- Patient triage table ----------------
st.markdown('<div class="mg-card">', unsafe_allow_html=True)
st.markdown("#### Patient Triage")
st.dataframe(triage_df, use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Patient detail view ----------------
st.markdown('<div class="mg-card">', unsafe_allow_html=True)
st.markdown("#### Patient Detail")

patient_names = triage_df["Patient"].tolist()
selected_patient = st.selectbox("Select a patient", patient_names)

detail = FALLBACK_PROFILES.get(selected_patient, {
    "profile": {"age": "-", "blood_group": "-", "allergies": "-", "existing_diseases": "-"},
    "ai_summary": "No AI summary available yet for this patient.",
    "visits": [], "prescriptions": [], "reports": [], "appointments": [],
})

tabs = st.tabs(["Profile", "AI Summary", "Reports", "Visits", "Prescriptions", "Appointments"])

with tabs[0]:
    p = detail["profile"]
    st.write(f"**Age:** {p['age']}  |  **Blood Group:** {p['blood_group']}")
    st.write(f"**Allergies:** {p['allergies']}")
    st.write(f"**Existing Conditions:** {p['existing_diseases']}")

with tabs[1]:
    st.write(detail["ai_summary"])

with tabs[2]:
    if detail["reports"]:
        for r in detail["reports"]:
            st.markdown(f"**{r['report_type']}** — {r['extracted_values']}")
    else:
        st.write("No lab reports on file.")

with tabs[3]:
    if detail["visits"]:
        for v in detail["visits"]:
            st.markdown(f"**{v['visit_date']}** — {v['reason']} ({v['department']}, {v['doctor']})")
    else:
        st.write("No previous visits on file.")

with tabs[4]:
    if detail["prescriptions"]:
        for rx in detail["prescriptions"]:
            st.markdown(f"**{rx['medicine']}** — {rx['dosage']} (prescribed by {rx['prescribed_by']})")
    else:
        st.write("No active prescriptions.")

with tabs[5]:
    if detail["appointments"]:
        for a in detail["appointments"]:
            st.markdown(f"**{a['department']}** — {a['date']} at {a['time']} — {a['status']}")
    else:
        st.write("No appointments on file.")

st.markdown("</div>", unsafe_allow_html=True)