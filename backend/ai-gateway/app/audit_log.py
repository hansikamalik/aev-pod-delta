import sqlite3
import json
import uuid
from datetime import datetime, timedelta
import os

DB_PATH = os.getenv("DB_PATH", "ai_gateway.db")

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Run migrations to ensure tables exist."""
    migration_path = os.path.join(os.path.dirname(__file__), "..", "migrations", "001_create_ai_interactions.sql")
    with _get_connection() as conn:
        with open(migration_path, "r") as f:
            conn.executescript(f.read())
        conn.commit()

def log_interaction(user_id: str, prompt: str, response: str, tokens: int, cost: float, citations: list):
    """Insert a row per interaction."""
    interaction_id = str(uuid.uuid4())
    citations_json = json.dumps(citations) if citations else "[]"
    
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_interactions (id, user_id, prompt, response, total_tokens, cost, citations)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (interaction_id, user_id, prompt, response, tokens, cost, citations_json)
        )
        conn.commit()
    return interaction_id

def update_fact_check(interaction_id: str, passed: bool, details: str = None):
    """Update fact check result for an interaction."""
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE ai_interactions
            SET fact_check_passed = ?, fact_check_details = ?
            WHERE id = ?
            """,
            (passed, details, interaction_id)
        )
        conn.commit()

def cleanup_expired_rows():
    """1-year retention policy cleanup job for expired rows."""
    one_year_ago = datetime.utcnow() - timedelta(days=365)
    with _get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM ai_interactions WHERE created_at < ?",
            (one_year_ago.isoformat(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
    return deleted_count
