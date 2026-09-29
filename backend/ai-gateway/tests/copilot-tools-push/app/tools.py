"""
Tool registry + dispatcher for the copilot.

Flow of dispatch_tool():
  unknown tool -> permission (RBAC) -> argument validation -> run tool

Permission is checked before argument validation on purpose, so a caller who
isn't allowed to use a tool learns nothing about its arguments.

NOTE: schemas for risk_score_get / asset_search / exposure_query below are
minimal placeholders inferred from the tests. Merge with your existing ones.
"""

from __future__ import annotations

from app import copilot_tools


class ToolError(Exception):
    pass


_TOOL_REGISTRY: dict = {}


# ---------------------------------------------------------
# Schemas (source of truth for what's advertised AND validated)
# ---------------------------------------------------------

def _schema(name, description, properties, required=()):
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": properties, "required": list(required)},
    }


_TOOL_SCHEMAS = {
    "risk_score_get": _schema(
        "risk_score_get",
        "Get the current risk score for an asset.",
        {"asset_id": {"type": "string", "description": "Asset identifier, e.g. db-prod-01"}},
        required=["asset_id"],
    ),
    "asset_search": _schema(
        "asset_search",
        "Search assets by free-text query.",
        {"query": {"type": "string"}},
        required=["query"],
    ),
    "exposure_query": _schema(
        "exposure_query",
        "List exposures, optionally filtered by asset or severity.",
        {"asset_id": {"type": "string"}, "severity": {"type": "string"}},
    ),
    "workflow_assist": _schema(
        "workflow_assist",
        "List, describe, or run a security workflow. Runs are dry runs unless "
        "dry_run is explicitly false; confirm with the user before a real run.",
        {
            "action": {"type": "string", "enum": ["list", "describe", "run"]},
            "workflow_id": {"type": "string", "description": "Required for describe and run"},
            "params": {"type": "object", "description": "Workflow parameters, e.g. {\"asset_id\": \"db-prod-01\"}"},
            "dry_run": {"type": "boolean", "description": "Defaults to true"},
        },
        required=["action"],
    ),
    "policy_check": _schema(
        "policy_check",
        "Check whether a resource configuration violates security policies.",
        {
            "resource_type": {
                "type": "string",
                "enum": ["storage_bucket", "database", "user_account", "firewall_rule"],
            },
            "config": {"type": "object", "description": "The resource's configuration to evaluate"},
            "policy_ids": {"type": "array", "description": "Limit to these policies; default is all that apply"},
        },
        required=["resource_type", "config"],
    ),
    "audit_query": _schema(
        "audit_query",
        "Search audit logs, e.g. who changed a config in the last week.",
        {
            "resource": {"type": "string", "description": "Substring match on resource name"},
            "actor": {"type": "string"},
            "action": {"type": "string", "description": "e.g. config.update, role.grant"},
            "since_days": {"type": "integer", "description": "Lookback window, 1-90, default 7"},
            "limit": {"type": "integer", "description": "Max entries, 1-200, default 50"},
        },
    ),
    "integration_list": _schema(
        "integration_list",
        "List connected third-party integrations (Defender, GitHub, ...) and their status.",
        {"status": {"type": "string", "enum": ["connected", "disconnected", "error"]}},
    ),
}


# ---------------------------------------------------------
# RBAC. Roles not listed here (e.g. "anonymous") get nothing.
# ---------------------------------------------------------

_ALL_TOOLS = set(_TOOL_SCHEMAS)

_ROLE_PERMISSIONS = {
    "admin": _ALL_TOOLS,
    "analyst": {
        "risk_score_get", "asset_search", "exposure_query",
        "workflow_assist", "policy_check", "integration_list",
    },
    "auditor": {"audit_query", "policy_check", "integration_list"},
    "viewer": {"asset_search", "integration_list"},
}


def _is_permitted(role: str, tool_name: str) -> bool:
    return tool_name in _ROLE_PERMISSIONS.get(role, set())


# ---------------------------------------------------------
# Registration
# ---------------------------------------------------------

def register_tool(name: str):
    def decorator(fn):
        if name in _TOOL_REGISTRY:
            raise ToolError(f"Tool '{name}' is already registered")
        if name not in _TOOL_SCHEMAS:
            raise ToolError(f"Tool '{name}' has no schema defined")
        _TOOL_REGISTRY[name] = fn
        return fn

    return decorator


def get_registered_tools() -> dict:
    return dict(_TOOL_REGISTRY)


def get_tool_schemas() -> list:
    """Only tools with an implementation are advertised to the model."""
    return [_TOOL_SCHEMAS[name] for name in _TOOL_REGISTRY]


# ---------------------------------------------------------
# Dispatch
# ---------------------------------------------------------

_JSON_TYPES = {"string": str, "integer": int, "boolean": bool, "object": dict, "array": list}


def _type_ok(value, expected: str) -> bool:
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _JSON_TYPES[expected])


def _validate_arguments(schema: dict, arguments: dict):
    """Return an error string, or None if the arguments are valid."""
    spec = schema["input_schema"]
    props = spec["properties"]

    missing = [a for a in spec["required"] if a not in arguments]
    if missing:
        return f"Missing required argument(s): {', '.join(missing)}"

    unexpected = [a for a in arguments if a not in props]
    if unexpected:
        return f"Unexpected argument(s): {', '.join(unexpected)}"

    for arg, value in arguments.items():
        prop = props[arg]
        if "type" in prop and not _type_ok(value, prop["type"]):
            return f"Argument '{arg}' must be of type {prop['type']}"
        if "enum" in prop and value not in prop["enum"]:
            return f"Argument '{arg}' must be one of: {', '.join(prop['enum'])}"
    return None


def _response(ok: bool, result=None, error=None) -> dict:
    return {"ok": ok, "result": result, "error": error}


def dispatch_tool(name: str, arguments: dict, user_id: str, role: str) -> dict:
    fn = _TOOL_REGISTRY.get(name)
    if fn is None:
        return _response(False, error=f"Unknown tool: {name}")

    if not _is_permitted(role, name):
        return _response(False, error=f"Role '{role}' is not permitted to use '{name}'")

    problem = _validate_arguments(_TOOL_SCHEMAS[name], arguments or {})
    if problem:
        return _response(False, error=problem)

    try:
        result = fn(user_id=user_id, **(arguments or {}))
    except Exception as exc:  # a broken tool must not take down the request
        return _response(False, error=f"{name} failed: {exc}")

    return _response(True, result=result)


# ---------------------------------------------------------
# Register the copilot tools
# ---------------------------------------------------------

register_tool("workflow_assist")(copilot_tools.workflow_assist)
register_tool("policy_check")(copilot_tools.policy_check)
register_tool("audit_query")(copilot_tools.audit_query)
register_tool("integration_list")(copilot_tools.integration_list)
