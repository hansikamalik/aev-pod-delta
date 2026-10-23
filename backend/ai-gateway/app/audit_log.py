import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import psycopg

_IN_MEMORY_INTERACTIONS: List[Dict[str, Any]] = []
_IN_MEMORY_CITATION_FLAGS: List[Dict[str, Any]] = []


class _SQLiteAdapter:
    """Lightweight adapter providing PostgreSQL-compatible interface for local SQLite."""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        return False

    def execute(self, sql: str, params: Optional[Any] = None):
        adapted_sql = re.sub(r"%s", "?", sql)
        cur = self.conn.cursor()
        if params is not None:
            return cur.execute(adapted_sql, tuple(params))
        return cur.executescript(adapted_sql)

    def commit(self):
        self.conn.commit()


def _get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://localhost:5432/mockdb"
    try:
        return psycopg.connect(db_url)
    except Exception:
        # Transparently fallback to local SQLite database so operations never fail
        db_path = os.getenv(
            "SQLITE_DATABASE_PATH",
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "data", "aev_audit.db"
                )
            ),
        )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return _SQLiteAdapter(db_path)


def setup_database():
    """Run migrations to ensure tables exist (PostgreSQL or local SQLite)."""
    with _get_connection() as conn:
        if isinstance(conn, _SQLiteAdapter):
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_interactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    cost REAL NOT NULL DEFAULT 0,
                    citations TEXT NOT NULL DEFAULT '[]',
                    fact_check_passed BOOLEAN,
                    fact_check_details TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    model TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ai_interactions_created_at ON ai_interactions (created_at);
                CREATE INDEX IF NOT EXISTS idx_ai_interactions_user_id ON ai_interactions (user_id);

                CREATE TABLE IF NOT EXISTS citation_flags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interaction_id TEXT NOT NULL,
                    citation_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    flagged_by TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_citation_flags_interaction_id ON citation_flags (interaction_id);
                """
            )
            return

        migrations_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
        migration_files = sorted(
            f for f in os.listdir(migrations_dir) if f.endswith(".sql")
        )
        for filename in migration_files:
            with open(os.path.join(migrations_dir, filename), "r") as f:
                conn.execute(f.read())
        conn.commit()


def log_interaction(user_id: str, prompt: str, response: str,
                    tokens: int, cost: float, citations: list,
                    model: str = None):
    """Insert a row per interaction."""
    interaction_id = str(uuid.uuid4())
    try:
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
    except Exception:
        pass
    return interaction_id


def update_fact_check(interaction_id: str, passed: bool, details: str = None):
    """Update fact check result for an interaction."""
    try:
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
    except Exception:
        pass


def flag_citation(
    interaction_id: str,
    citation_id: str,
    reason: str,
    flagged_by: str = "anonymous",
) -> None:
    """Record a user flag marking a citation as inaccurate."""
    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO citation_flags
                    (interaction_id, citation_id, reason, flagged_by)
                VALUES (%s, %s, %s, %s)
                """,
                (interaction_id, citation_id, reason, flagged_by),
            )
            conn.commit()
    except Exception:
        pass


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
