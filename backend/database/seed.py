"""
MediAgent — Demo Data Seeder

Populates hospital.db with realistic sample patients, doctors,
visits, prescriptions, lab reports, and appointments so the Hospital
Dashboard and Patient Portal have something to show out of the box.

Run: python -m backend.database.seed
"""

from datetime import datetime, timedelta

from backend.database.schema import init_db
from backend.tools.database_tool import execute, get_connection


def clear_tables():
    with get_connection() as conn:
        for table in ["appointments", "lab_reports", "prescriptions", "visits", "doctors", "patients"]:
            conn.execute(f"DELETE FROM {table}")


def seed():
    init_db()
    clear_tables()

    today = datetime.now()

    # --- Doctors ---
    doctors = [
        ("Dr. Ananya Rao", "General Medicine", 1),
        ("Dr. Vikram Sharma", "Cardiology", 1),
        ("Dr. Priya Menon", "Dermatology", 1),
        ("Dr. Karthik Iyer", "Orthopedics", 0),
        ("Dr. Fatima Sheikh", "Pediatrics", 1),
        ("Dr. Rohan Das", "Emergency Medicine", 1),
    ]
    doctor_ids = []
    for name, dept, available in doctors:
        doctor_ids.append(execute(
            "INSERT INTO doctors (name, department, available) VALUES (?, ?, ?)",
            (name, dept, available),
        ))

    # --- Patients ---
    patients = [
        ("Aarav Mehta", 34, "O+", "Penicillin", "Hypertension"),
        ("Sneha Kapoor", 27, "A+", "None", "None"),
        ("Ramesh Iyer", 61, "B+", "Sulfa drugs", "Type 2 Diabetes"),
        ("Divya Nair", 45, "AB+", "None", "Asthma"),
        ("Kabir Singh", 19, "O-", "None", "None"),
    ]
    patient_ids = []
    for name, age, bg, allergies, diseases in patients:
        patient_ids.append(execute(
            "INSERT INTO patients (name, age, blood_group, allergies, existing_diseases) VALUES (?, ?, ?, ?, ?)",
            (name, age, bg, allergies, diseases),
        ))

    # --- Visits ---
    visits = [
        (patient_ids[0], (today - timedelta(days=14)).strftime("%Y-%m-%d"), "Chest discomfort", "Cardiology", "Dr. Vikram Sharma", "ECG normal, advised follow-up"),
        (patient_ids[1], (today - timedelta(days=30)).strftime("%Y-%m-%d"), "Skin rash", "Dermatology", "Dr. Priya Menon", "Prescribed topical cream"),
        (patient_ids[2], (today - timedelta(days=5)).strftime("%Y-%m-%d"), "Routine diabetes checkup", "General Medicine", "Dr. Ananya Rao", "HbA1c stable"),
        (patient_ids[3], (today - timedelta(days=2)).strftime("%Y-%m-%d"), "Shortness of breath", "Emergency Medicine", "Dr. Rohan Das", "Nebulizer administered, stabilized"),
        (patient_ids[4], (today - timedelta(days=60)).strftime("%Y-%m-%d"), "Sports injury", "Orthopedics", "Dr. Karthik Iyer", "X-ray clear, rest advised"),
    ]
    for patient_id, date, reason, dept, doctor, notes in visits:
        execute(
            "INSERT INTO visits (patient_id, visit_date, reason, department, doctor, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, date, reason, dept, doctor, notes),
        )

    # --- Prescriptions ---
    prescriptions = [
        (patient_ids[0], "Amlodipine 5mg", "Once daily", (today - timedelta(days=14)).strftime("%Y-%m-%d"), "Dr. Vikram Sharma"),
        (patient_ids[2], "Metformin 500mg", "Twice daily", (today - timedelta(days=5)).strftime("%Y-%m-%d"), "Dr. Ananya Rao"),
        (patient_ids[3], "Salbutamol Inhaler", "As needed", (today - timedelta(days=2)).strftime("%Y-%m-%d"), "Dr. Rohan Das"),
    ]
    for patient_id, medicine, dosage, date, doctor in prescriptions:
        execute(
            "INSERT INTO prescriptions (patient_id, medicine, dosage, prescribed_on, prescribed_by) VALUES (?, ?, ?, ?, ?)",
            (patient_id, medicine, dosage, date, doctor),
        )

    # --- Lab reports ---
    lab_reports = [
        (patient_ids[0], "Lipid Panel", "docs/sample_reports/aarav_lipid.pdf", (today - timedelta(days=14)).strftime("%Y-%m-%d"), "LDL: 142 mg/dL (High)"),
        (patient_ids[2], "HbA1c", "docs/sample_reports/ramesh_hba1c.pdf", (today - timedelta(days=5)).strftime("%Y-%m-%d"), "HbA1c: 6.8% (Elevated)"),
    ]
    for patient_id, report_type, path, date, values in lab_reports:
        execute(
            "INSERT INTO lab_reports (patient_id, report_type, file_path, uploaded_on, extracted_values) VALUES (?, ?, ?, ?, ?)",
            (patient_id, report_type, path, date, values),
        )

    # --- Appointments (today/upcoming, for the dashboard triage table) ---
    appointments = [
        (patient_ids[0], doctor_ids[1], "Cardiology", today.strftime("%Y-%m-%d"), "10:30 AM", "204", "confirmed", "High"),
        (patient_ids[1], doctor_ids[2], "Dermatology", today.strftime("%Y-%m-%d"), "11:15 AM", "112", "confirmed", "Low"),
        (patient_ids[2], doctor_ids[0], "General Medicine", today.strftime("%Y-%m-%d"), "12:00 PM", "108", "confirmed", "Medium"),
        (patient_ids[3], doctor_ids[5], "Emergency Medicine", today.strftime("%Y-%m-%d"), "09:00 AM", "ER-2", "in_progress", "Critical"),
        (patient_ids[4], doctor_ids[3], "Orthopedics", (today + timedelta(days=1)).strftime("%Y-%m-%d"), "02:30 PM", "305", "confirmed", "Low"),
    ]
    for patient_id, doctor_id, dept, date, time, room, status, _priority in appointments:
        execute(
            """INSERT INTO appointments (patient_id, doctor_id, department, date, time, room_number, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, doctor_id, dept, date, time, room, status),
        )

    print(f"Seeded {len(patients)} patients, {len(doctors)} doctors, "
          f"{len(visits)} visits, {len(appointments)} appointments.")


if __name__ == "__main__":
    seed()