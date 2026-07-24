# MediAgent

**Intelligent AI Care Coordination for Patients and Hospitals**

MediAgent is an Agentic AI Hospital Care Coordination Platform. It is
not a chatbot, symptom checker, or hospital management system — it's
an AI Care Coordinator that autonomously decides which specialist AI
agents should collaborate to solve a healthcare request.

## Architecture

Every request starts with the **Supervisor Agent**, which understands
intent, builds a dynamic execution plan, and routes to only the
specialist agents required:

- **Medical Agent** — symptom assessment, risk level, suggested department/tests
- **Records Agent** — EHR: history, allergies, prescriptions, visits
- **Appointment Agent** — doctor search, booking, rescheduling
- **Knowledge Agent (RAG)** — diseases, policies, guidelines, FAQs
- **Safety Agent** — always runs last; detects emergencies, cannot be skipped

There is no fixed pipeline — different requests produce completely
different execution paths.

## Project Structure

```
Hospital-Agent-AI/
├── backend/
│   ├── agents/          # Supervisor + specialist agents
│   ├── workflow/         # LangGraph graph + shared state
│   ├── database/         # SQLite schema
│   ├── rag/               # Document ingestion + retrieval
│   ├── reports/           # Medical report OCR/PDF analysis
│   ├── notifications/     # WhatsApp (mock/Twilio)
│   ├── navigation/        # Nearby hospitals (mock/Google Maps)
│   ├── tools/              # LLM, DB, and search helper tools
│   ├── api/                 # FastAPI routes
│   ├── config.py
│   └── main.py
├── frontend/
│   ├── patient_portal.py
│   ├── hospital_dashboard.py
│   └── styles.css
├── docs/                   # Hospital guidelines + sample reports for RAG
├── requirements.txt
└── Dockerfile
```

## Getting Started

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# fill in GEMINI_API_KEY at minimum

# 3. Initialize the database
python -m backend.database.schema

# 4. Build the RAG index
python -m backend.rag.ingest

# 5. Run the backend
uvicorn backend.main:app --reload

# 6. Run a frontend (in a separate terminal)
streamlit run frontend/patient_portal.py
# or
streamlit run frontend/hospital_dashboard.py
```

## Status

This is a starter scaffold: folder structure, shared state schema,
the Supervisor's routing skeleton, and stub implementations for every
agent/tool/service are in place. LLM calls, RAG embeddings, OCR
extraction, and real Maps/WhatsApp integrations are marked `TODO` for
implementation.

## Future Scope

- Real Google Maps API integration
- Real Twilio WhatsApp integration
- Real hospital EHR integration (FHIR/HL7 compatible)
- Voice assistant
- Wearable device integration
