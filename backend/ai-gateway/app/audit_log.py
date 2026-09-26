import json
import uuid
from datetime import datetime, timedelta, timezone

import psycopg


def _get_connection():
    return psycopg.connect(os.getenv("DATABASE_URL"))


import os  # noqa: E402


def setup_database():
    """Run migrations to ensure tables exist."""
    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "migrations",
        "001_create_ai_interactions.sql"
    )
    with _get_connection() as conn:
        with open(migration_path, "r") as f:
            conn.execute(f.read())
        conn.commit()


def log_interaction(user_id: str, prompt: str, response: str,
                    tokens: int, cost: float, citations: list):
    """Insert a row per interaction."""
    interaction_id = str(uuid.uuid4())
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_interactions
                (id, user_id, prompt, response, total_tokens, cost, citations)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (interaction_id, user_id, prompt, response, tokens, cost,
             json.dumps(citations or [])),
        )
        conn.commit()
    return interaction_id


def update_fact_check(interaction_id: str, passed: bool, details: str = None):
    """Update fact check result for an interaction."""
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE ai_interactions
            SET fact_check_passed = %s, fact_check_details = %s
            WHERE id = %s
            """,
            (passed, details, interaction_id),
        )
        conn.commit()


def cleanup_expired_rows():
    """1-year retention policy cleanup job for expired rows."""
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    with _get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM ai_interactions WHERE created_at < %s",
            (one_year_ago,),
        )
        deleted_count = cur.rowcount
        conn.commit()
    return deleted_count
