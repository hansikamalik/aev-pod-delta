"""Tests for P0-3: Gemma Dynamic Tool Calling & Reasoning Engine."""

from typing import Any, Dict
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.tool_router import (
    get_gemini_tools,
    resolve_dynamic_tool_intent,
)
from app.tools import TOOL_SCHEMAS


def _patch_gateway(monkeypatch, captured_prompt_container=None):
    """Patch ask_gpt, check_rate_limit, and database to run offline."""
    def mock_ask_gpt(question, tools=None):
        if captured_prompt_container is not None:
            captured_prompt_container["question"] = question
            captured_prompt_container["tools"] = tools
        return {
            "answer": f"Analysis based on tool data for: {question[:40]}...",
            "model": "gemma-4-31b-it",
            "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
        }

    monkeypatch.setattr("app.main.ask_gpt", mock_ask_gpt)
    monkeypatch.setattr(
        "app.main.check_rate_limit",
        lambda user_id, org_tier="free": {
            "allowed": True,
            "tokens_remaining": 50,
            "bucket_capacity": 100,
            "org_tier": org_tier,
        },
    )
    monkeypatch.setattr("app.main.setup_database", lambda: None)
    monkeypatch.setattr("app.main.log_interaction", lambda **kwargs: "test-int-id")


def _ask(question: str, role: str = "analyst", user_id: str = "analyst-1"):
    headers = {"X-User-ID": user_id, "X-User-Role": role}
    with TestClient(app) as client:
        return client.post("/copilot/query", headers=headers, json={"question": question})


# --- 1. Tool Declaration & Schema Generation ---

def test_gemini_tools_declarations_generated():
    tool_decl = get_gemini_tools()
    assert tool_decl is not None
    assert hasattr(tool_decl, "function_declarations")
    names = {fd.name for fd in tool_decl.function_declarations}
    expected = {s["name"] for s in TOOL_SCHEMAS}
    assert names == expected
    assert "risk_score_get" in names
    assert "exposure_query" in names
    assert "asset_search" in names
    assert "policy_check" in names
    assert "workflow_assist" in names
    assert "audit_query" in names
    assert "integration_list" in names
    assert "report_generate" in names


# --- 2. Dynamic Tool Intent Parsing ---

def test_intent_parsing_risk_score():
    tool, args = resolve_dynamic_tool_intent("What is the security posture and risk of asset-001?")
    assert tool == "risk_score_get"
    assert args["asset_id"] == "asset-001"


def test_intent_parsing_exposure_severity():
    tool, args = resolve_dynamic_tool_intent("Show me critical exposures on our infrastructure")
    assert tool == "exposure_query"
    assert args["severity"] == "critical"


def test_intent_parsing_asset_search():
    tool, args = resolve_dynamic_tool_intent("Find database servers in production")
    assert tool == "asset_search"
    assert "database" in args["query"]


def test_intent_parsing_report_generate():
    tool, args = resolve_dynamic_tool_intent("Generate security report for asset-001")
    assert tool == "report_generate"
    assert args["asset_id"] == "asset-001"
    assert args["report_type"] == "security"


def test_intent_parsing_workflow_assist():
    tool, args = resolve_dynamic_tool_intent("List all available remediation workflows")
    assert tool == "workflow_assist"
    assert args["action"] == "list"


def test_intent_parsing_policy_check():
    tool, args = resolve_dynamic_tool_intent("Check policy compliance for storage bucket with public access")
    assert tool == "policy_check"
    assert args["resource_type"] == "storage_bucket"
    assert args["config"]["public_access"] is True


def test_intent_parsing_audit_query():
    tool, args = resolve_dynamic_tool_intent("Show audit logs for user:hansika")
    assert tool == "audit_query"
    assert args["actor"] == "hansika"


def test_intent_parsing_integration_list():
    tool, args = resolve_dynamic_tool_intent("List all connected integrations and connectors")
    assert tool == "integration_list"
    assert args["status"] == "connected"


# --- 3. End-to-End Dynamic Tool Execution via /copilot/query ---

def test_copilot_triggers_exposure_query_dynamically(monkeypatch):
    seen = {}
    _patch_gateway(monkeypatch, seen)
    res = _ask("What are our critical vulnerabilities?", role="analyst")
    assert res.status_code == 200
    data = res.json()
    assert data["tool_call"] is not None
    assert data["tool_call"]["tool"] == "exposure_query"
    assert data["tool_call"]["ok"] is True
    assert "Verified data from the exposure_query tool" in seen["question"]
    assert len(data["citations"]) >= 1


def test_copilot_triggers_policy_check_dynamically(monkeypatch):
    seen = {}
    _patch_gateway(monkeypatch, seen)
    res = _ask("Check policy compliance for storage bucket with public access", role="analyst")
    assert res.status_code == 200
    data = res.json()
    assert data["tool_call"] is not None
    assert data["tool_call"]["tool"] == "policy_check"
    assert data["tool_call"]["ok"] is True
    assert data["tool_call"]["result"]["compliant"] is False
    assert any(c.get("type") == "policy" for c in data["citations"])


def test_copilot_triggers_report_generate_dynamically(monkeypatch):
    seen = {}
    _patch_gateway(monkeypatch, seen)
    res = _ask("Generate security report for asset-001", role="analyst")
    assert res.status_code == 200
    data = res.json()
    assert data["tool_call"] is not None
    assert data["tool_call"]["tool"] == "report_generate"
    assert data["tool_call"]["ok"] is True
    assert any(c.get("type") == "report" for c in data["citations"])


def test_copilot_triggers_integration_list_dynamically(monkeypatch):
    seen = {}
    _patch_gateway(monkeypatch, seen)
    res = _ask("Show connected integrations", role="viewer")
    assert res.status_code == 200
    data = res.json()
    assert data["tool_call"] is not None
    assert data["tool_call"]["tool"] == "integration_list"
    assert data["tool_call"]["ok"] is True


def test_copilot_triggers_workflow_assist_dynamically(monkeypatch):
    seen = {}
    _patch_gateway(monkeypatch, seen)
    res = _ask("List available workflows", role="admin")
    assert res.status_code == 200
    data = res.json()
    assert data["tool_call"] is not None
    assert data["tool_call"]["tool"] == "workflow_assist"
    assert data["tool_call"]["ok"] is True


# --- 4. Role-Based Access Control (RBAC) Hard Enforcement ---

def test_viewer_denied_exposure_query(monkeypatch):
    _patch_gateway(monkeypatch)
    res = _ask("Show critical exposures", role="viewer")
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "Permission denied"
    assert "exposure_query" in res.json()["detail"]["reason"]


def test_viewer_denied_policy_check(monkeypatch):
    _patch_gateway(monkeypatch)
    res = _ask("Check policy compliance on storage bucket", role="viewer")
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "Permission denied"
    assert "policy_check" in res.json()["detail"]["reason"]


def test_auditor_denied_risk_tool_but_allowed_audit(monkeypatch):
    _patch_gateway(monkeypatch)
    # Auditor cannot check risk score
    res_risk = _ask("How risky is asset-001?", role="auditor")
    assert res_risk.status_code == 403
    assert "risk_score_get" in res_risk.json()["detail"]["reason"]

    # Auditor is allowed audit query
    monkeypatch.setattr("app.copilot_tools.query_interactions", lambda **kw: [])
    res_audit = _ask("Show audit logs for user hansika", role="auditor")
    assert res_audit.status_code == 200
    assert res_audit.json()["tool_call"]["tool"] == "audit_query"
