import json
import uuid
from datetime import datetime, timedelta, timezone

import psycopg


def _get_connection():
    return psycopg.connect(os.getenv("DATABASE_URL"))


import os  # noqa: E402


def setup_database():
    """Run every migration file, in order, to ensure tables exist."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
    migration_files = sorted(
        f for f in os.listdir(migrations_dir) if f.endswith(".sql")
    )
    with _get_connection() as conn:
        for filename in migration_files:
            with open(os.path.join(migrations_dir, filename), "r") as f:
                conn.execute(f.read())
        conn.commit()


def log_interaction(user_id: str, prompt: str, response: str,
                    tokens: int, cost: float, citations: list,
                    model: str = None):
    """Insert a row per interaction."""
    interaction_id = str(uuid.uuid4())
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_interactions
                (id, user_id, prompt, response, total_tokens, cost, citations, model)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (interaction_id, user_id, prompt, response, tokens, cost,
             json.dumps(citations or []), model),
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


def query_interactions(
    user_id: str = None, model: str = None,
    start_date: str = None, end_date: str = None,
    limit: int = 50,
):
    """Filter ai_interactions by user, model and/or a date range.

    Every filter is optional. Only the ones actually passed in are
    applied. Results are newest first, capped at `limit`.
    """
    clauses = []
    params = []

    if user_id:
        clauses.append("user_id = %s")
        params.append(user_id)
    if model:
        clauses.append("model = %s")
        params.append(model)
    if start_date:
        clauses.append("created_at >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("created_at <= %s")
        params.append(end_date)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    with _get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT id, user_id, model, total_tokens, cost, citations,
                   fact_check_passed, created_at
            FROM ai_interactions
            {where_sql}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            params,
        )
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    return rows