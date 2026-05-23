"""
retrieval/gap_tracker.py

When Claude can't answer a question from the knowledge base, we log it.
These become "knowledge gaps" — questions the team's documentation doesn't cover.
The admin panel surfaces these so someone can write the missing doc.

This is the feature that separates PitWall from a generic RAG demo.
"""
import sqlite3
import os
from datetime import datetime
from config import GAPS_DB_PATH


def _get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(GAPS_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(GAPS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the gaps table if it doesn't exist. Call on startup."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            gap_description TEXT,
            asked_at TEXT NOT NULL,
            resolved INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def log_gap(question: str, gap_description: str = ""):
    """Record a question the system couldn't answer."""
    conn = _get_connection()
    conn.execute(
        "INSERT INTO knowledge_gaps (question, gap_description, asked_at) VALUES (?, ?, ?)",
        (question, gap_description, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_gaps(resolved: bool = False, limit: int = 50) -> list[dict]:
    """Return logged knowledge gaps, newest first."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM knowledge_gaps WHERE resolved = ? ORDER BY asked_at DESC LIMIT ?",
        (1 if resolved else 0, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def resolve_gap(gap_id: int):
    """Mark a gap as resolved (e.g. after someone writes the missing doc)."""
    conn = _get_connection()
    conn.execute("UPDATE knowledge_gaps SET resolved = 1 WHERE id = ?", (gap_id,))
    conn.commit()
    conn.close()


def gap_count() -> int:
    conn = _get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM knowledge_gaps WHERE resolved = 0"
    ).fetchone()[0]
    conn.close()
    return count
