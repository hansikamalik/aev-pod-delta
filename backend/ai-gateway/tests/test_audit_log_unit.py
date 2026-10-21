"""Tests for audit_log functions with mocked PostgreSQL connection."""

from unittest.mock import MagicMock, patch
from app.audit_log import (
    setup_database,
    log_interaction,
    update_fact_check,
    cleanup_expired_rows,
    query_interactions,
)


def test_setup_database(tmp_path):
    mock_conn = MagicMock()
    with patch("app.audit_log._get_connection", return_value=mock_conn):
        setup_database()
        assert mock_conn.__enter__.return_value.execute.called
        assert mock_conn.__enter__.return_value.commit.called


def test_log_interaction():
    mock_conn = MagicMock()
    with patch("app.audit_log._get_connection", return_value=mock_conn):
        iid = log_interaction(
            user_id="user-123",
            prompt="What is IAM?",
            response="IAM is Identity and Access Management",
            tokens=45,
            cost=0.001,
            citations=[{"id": "cit-1"}],
            model="gemma-4-31b-it",
        )
        assert isinstance(iid, str)
        assert len(iid) > 10
        assert mock_conn.__enter__.return_value.execute.called
        assert mock_conn.__enter__.return_value.commit.called


def test_update_fact_check():
    mock_conn = MagicMock()
    with patch("app.audit_log._get_connection", return_value=mock_conn):
        update_fact_check("interact-1", passed=True, details="Verified against live asset")
        assert mock_conn.__enter__.return_value.execute.called
        assert mock_conn.__enter__.return_value.commit.called


def test_cleanup_expired_rows():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.rowcount = 5
    mock_conn.__enter__.return_value.execute.return_value = mock_cur
    with patch("app.audit_log._get_connection", return_value=mock_conn):
        count = cleanup_expired_rows()
        assert count == 5
        assert mock_conn.__enter__.return_value.commit.called


def test_query_interactions_all_filters():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.description = [
        ("id",), ("user_id",), ("model",), ("total_tokens",),
        ("cost",), ("citations",), ("fact_check_passed",), ("created_at",)
    ]
    mock_cur.fetchall.return_value = [
        ("id-1", "user-1", "gemma", 10, 0.0, "[]", True, "2026-10-01")
    ]
    mock_conn.__enter__.return_value.execute.return_value = mock_cur

    with patch("app.audit_log._get_connection", return_value=mock_conn):
        rows = query_interactions(
            user_id="user-1",
            model="gemma",
            start_date="2026-10-01",
            end_date="2026-10-10",
            limit=25,
        )
        assert len(rows) == 1
        assert rows[0]["user_id"] == "user-1"


def test_query_interactions_no_filters():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.description = [("id",), ("user_id",)]
    mock_cur.fetchall.return_value = [("id-1", "user-1")]
    mock_conn.__enter__.return_value.execute.return_value = mock_cur

    with patch("app.audit_log._get_connection", return_value=mock_conn):
        rows = query_interactions()
        assert len(rows) == 1
