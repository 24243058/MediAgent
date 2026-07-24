"""
MediAgent — Database Schema

Defines and initializes the simplified EHR SQLite schema.
Run `python -m backend.database.schema` to (re)create hospital.db.
"""

from backend.tools.database_tool import get_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    age             INTEGER,
    blood_group     TEXT,
    allergies       TEXT,
    existing_diseases TEXT
);

CREATE TABLE IF NOT EXISTS visits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    visit_date      TEXT NOT NULL,
    reason          TEXT,
    department      TEXT,
    doctor          TEXT,
    notes           TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    medicine        TEXT NOT NULL,
    dosage          TEXT,
    prescribed_on   TEXT,
    prescribed_by   TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    report_type     TEXT,
    file_path       TEXT,
    uploaded_on     TEXT,
    extracted_values TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE IF NOT EXISTS doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    department      TEXT NOT NULL,
    available       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS appointments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    doctor_id       INTEGER NOT NULL,
    department      TEXT,
    date            TEXT,
    time            TEXT,
    room_number     TEXT,
    status          TEXT DEFAULT 'confirmed',
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);
"""


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    print("MediAgent database initialized.")


if __name__ == "__main__":
    init_db()
