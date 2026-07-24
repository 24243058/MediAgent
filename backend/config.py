"""
MediAgent — Central Configuration

Loads environment variables and exposes app-wide settings.
Replace mock/demo flags with real credentials for production.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Every part of the app imports settings from here, so loading .env in this
# one place (before any os.getenv() call below) guarantees it's picked up
# everywhere — the FastAPI backend, both Streamlit apps, and the seed/ingest
# scripts — regardless of which entrypoint actually launches the process.
load_dotenv()


@dataclass
class Settings:
    # --- App ---
    APP_NAME: str = "MediAgent"
    APP_TAGLINE: str = "Intelligent AI Care Coordination for Patients and Hospitals"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # --- LLM ---
    # LLM_PROVIDER: "gemini" (default) or "groq" — both power the Supervisor's
    # ReAct planning and the Knowledge Agent's grounded answers via the same
    # call_llm() interface in tools/llm.py.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Default model: 2.5 Flash is on Google's currently-supported free tier
    # lineup. Older models like 2.0-flash have been returning "limit: 0"
    # free-tier quota errors on many projects — if you hit that, this is
    # the first thing to check/change.
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # --- Database ---
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "backend/database/hospital.db")

    # --- RAG ---
    RAG_DOCS_DIR: str = os.getenv("RAG_DOCS_DIR", "docs")
    RAG_INDEX_DIR: str = os.getenv("RAG_INDEX_DIR", "backend/rag/index")

    # --- Maps / Nearby Hospitals ---
    # MAPS_PROVIDER: "mock" (default, no setup), "osm" (free, no API key —
    # OpenStreetMap Overpass API), or "google" (requires GOOGLE_MAPS_API_KEY + billing)
    MAPS_PROVIDER: str = os.getenv("MAPS_PROVIDER", "mock").lower()
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    # Fallback location used until real per-patient geolocation is wired up
    # (default: Kovilpatti, Tamil Nadu). Override via env vars.
    DEFAULT_LATITUDE: float = float(os.getenv("DEFAULT_LATITUDE", "9.1698"))
    DEFAULT_LONGITUDE: float = float(os.getenv("DEFAULT_LONGITUDE", "77.8778"))

    # --- Twilio WhatsApp ---
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    USE_MOCK_WHATSAPP: bool = os.getenv("USE_MOCK_WHATSAPP", "true").lower() == "true"

    # --- API ---
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    def has_llm_key(self) -> bool:
        """True if the currently-selected LLM_PROVIDER has a key configured.
        Callers (supervisor.py, knowledge_agent.py) use this instead of
        checking GEMINI_API_KEY directly, so they work with either provider."""
        if self.LLM_PROVIDER == "groq":
            return bool(self.GROQ_API_KEY)
        return bool(self.GEMINI_API_KEY)


settings = Settings()