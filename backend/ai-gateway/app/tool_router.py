"""Dynamic tool calling and reasoning router for Gemma and the AI Gateway."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from app.tools import TOOL_SCHEMAS, dispatch_tool

ASSET_PATTERN = re.compile(r"\basset-[a-zA-Z0-9_-]+\b", re.IGNORECASE)
SEVERITY_PATTERN = re.compile(r"\b(low|medium|high|critical)\b", re.IGNORECASE)
REPORT_TYPE_PATTERN = re.compile(r"\b(security|risk|exposure)\b", re.IGNORECASE)
STATUS_PATTERN = re.compile(r"\b(connected|error|disconnected)\b", re.IGNORECASE)


def _clean_schema_for_gemini(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Strip unsupported keys like additionalProperties for Google GenAI schema validator."""
    if not isinstance(schema_dict, dict):
        return schema_dict
    clean = {
        k: v for k, v in schema_dict.items()
        if k not in ("additionalProperties", "additional_properties")
    }
    if "properties" in clean and isinstance(clean["properties"], dict):
        clean["properties"] = {
            pk: _clean_schema_for_gemini(pv)
            for pk, pv in clean["properties"].items()
        }
    return clean


def get_gemini_tools() -> Optional[Any]:
    """Convert registered TOOL_SCHEMAS to Google GenAI Tool declarations."""
    try:
        import sys
        genai = sys.modules.get("google.genai")
        if genai is not None and hasattr(genai, "types"):
            types = genai.types
        else:
            from google.genai import types

        function_declarations = []
        for schema in TOOL_SCHEMAS:
            clean_params = _clean_schema_for_gemini(schema.get("parameters", {}))
            fd = types.FunctionDeclaration(
                name=schema["name"],
                description=schema["description"],
                parameters=clean_params,
            )
            function_declarations.append(fd)

        return types.Tool(function_declarations=function_declarations)
    except Exception:
        return None


def resolve_dynamic_tool_intent(question: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Analyze natural language question and infer the intended tool and arguments.

    Returns:
        (tool_name, arguments_dict) or None if no tool is required.
    """
    q_lower = question.lower()
    asset_match = ASSET_PATTERN.search(question)
    asset_id = asset_match.group(0).lower() if asset_match else None

    # 1. Report Generation Intent
    if any(k in q_lower for k in [
        "generate report", "create report", "produce report", "export report", "security report for"
    ]):
        if asset_id:
            rep_type_match = REPORT_TYPE_PATTERN.search(q_lower)
            rep_type = rep_type_match.group(1).lower() if rep_type_match else "security"
            return "report_generate", {"asset_id": asset_id, "report_type": rep_type}

    # 2. Risk Score Intent
    # Questions mentioning asset-XXX or asking about risk/posture of an asset
    if asset_id and any(k in q_lower for k in [
        "risk", "score", "posture", "how risky", "threat level"
    ]):
        return "risk_score_get", {"asset_id": asset_id}
    if asset_id and not any(k in q_lower for k in [
        "exposure", "vulnerabilit", "cve", "report", "rescan"
    ]):
        # Default behavior: when an asset ID is specified without other tools, inspect risk
        return "risk_score_get", {"asset_id": asset_id}

    # 3. Exposure & Vulnerability Intent
    if any(k in q_lower for k in [
        "exposure", "vulnerabilit", "cve", "weakness", "flaw", "threat finding"
    ]):
        args: Dict[str, Any] = {}
        if asset_id:
            args["asset_id"] = asset_id
        sev_match = SEVERITY_PATTERN.search(q_lower)
        if sev_match:
            args["severity"] = sev_match.group(1).lower()
        return "exposure_query", args

    # 4. Policy Check Intent
    if any(k in q_lower for k in [
        "policy check", "check policy", "compliant", "compliance", "policy rule"
    ]):
        # Determine resource type and mock config from question context
        res_type = "storage_bucket"
        config = {"public_access": True, "encrypted": True}
        if "user" in q_lower or "account" in q_lower or "mfa" in q_lower:
            res_type = "user_account"
            config = {"mfa_enabled": "without" not in q_lower and "no" not in q_lower}
        elif "firewall" in q_lower or "port" in q_lower:
            res_type = "firewall_rule"
            config = {"open_admin_ports": "open" in q_lower}
        elif "storage" in q_lower or "bucket" in q_lower:
            res_type = "storage_bucket"
            config = {
                "public_access": "public" in q_lower,
                "encrypted": "encrypt" in q_lower,
            }
        return "policy_check", {"resource_type": res_type, "config": config}

    # 5. Workflow Assist Intent
    if any(k in q_lower for k in [
        "workflow", "playbook", "remediat", "run workflow", "dry run", "isolate"
    ]):
        action = "list"
        if "describe" in q_lower or "details" in q_lower:
            action = "describe"
        elif any(w in q_lower for w in ["run", "start", "execute", "isolate"]):
            action = "run"

        wf_args: Dict[str, Any] = {"action": action}
        if action in ("describe", "run"):
            wf_id = "isolate_host" if "isolate" in q_lower else "rescan_asset"
            wf_args["workflow_id"] = wf_id
            if action == "run":
                wf_args["dry_run"] = "dry" in q_lower or "simulate" in q_lower
                if wf_id == "isolate_host":
                    wf_args["params"] = {"host_id": "h-1"}
                else:
                    wf_args["params"] = {"asset_id": asset_id or "asset-001"}
        return "workflow_assist", wf_args

    # 6. Audit Query Intent
    if any(k in q_lower for k in [
        "audit log", "audit query", "who queried", "interaction log", "audit trail"
    ]):
        audit_args: Dict[str, Any] = {"since_days": 7, "limit": 10}
        actor_match = re.search(r"\buser[:\s]+([a-zA-Z0-9_-]+)", q_lower)
        if actor_match:
            audit_args["actor"] = actor_match.group(1)
        return "audit_query", audit_args

    # 7. Integration List Intent
    if any(k in q_lower for k in [
        "integration", "connected tool", "connectors", "third party status", "active integrations"
    ]):
        stat_match = STATUS_PATTERN.search(q_lower)
        int_args: Dict[str, Any] = {}
        if stat_match:
            int_args["status"] = stat_match.group(1).lower()
        return "integration_list", int_args

    # 8. Asset Search Intent
    search_keywords = [
        "search asset", "find asset", "find server", "find bucket",
        "find database", "locate asset", "search for"
    ]
    if any(k in q_lower for k in search_keywords):
        pattern = r"^(search (for|assets?)|find (assets?|servers?|buckets?)|locate)\s*"
        clean_query = re.sub(pattern, "", q_lower).strip()
        return "asset_search", {"query": clean_query or "all"}

    return None


def execute_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str,
    user_role: str,
) -> Dict[str, Any]:
    """Execute a single tool call with RBAC validation and structured result."""
    return dispatch_tool(
        tool_name=tool_name,
        arguments=arguments,
        user_id=user_id,
        role=user_role,
    )
