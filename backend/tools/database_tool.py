"""
MediAgent — Database Tool

Small helper around sqlite3 used by the Records and Appointment
agents. Swap this module out to point at a real hospital EHR later.
"""

import sqlite3
from contextlib import contextmanager

from backend.config import settings


@contextmanager
def get_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def execute(query: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE and return the last row id (if any)."""
    with get_connection() as conn:
        cursor = conn.execute(query, params)
        return cursor.lastrowid
