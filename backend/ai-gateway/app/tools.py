"""Tool registration, schemas, validation, and role-based dispatch."""

from typing import Any, Callable, Dict, List

from app.permissions import is_allowed


class ToolError(Exception):
    """Raised when a tool registration or execution contract is invalid."""


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "asset_search",
        "description": "Search assets using a natural-language query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language asset search query.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "exposure_query",
        "description": "Query asset exposure and vulnerability information.",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "risk_score_get",
        "description": "Retrieve the risk score for an asset.",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "string"},
            },
            "required": ["asset_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "report_generate",
        "description": "Generate a security report for an asset.",
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset identifier.",
                },
                "report_type": {
                    "type": "string",
                    "enum": ["security", "risk", "exposure"],
                    "description": "Type of report to generate.",
                },
            },
            "required": ["asset_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "workflow_assist",
        "description": "List, describe, dry-run, or start a supported workflow.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "describe", "run"],
                },
                "workflow_id": {"type": "string"},
                "params": {"type": "object"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    },
    {
        "name": "policy_check",
        "description": "Check a resource configuration against policy rules.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource_type": {"type": "string"},
                "config": {"type": "object"},
                "policy_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["resource_type", "config"],
            "additionalProperties": False,
        },
    },
    {
        "name": "audit_query",
        "description": "Query audit events with optional filters.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource": {"type": "string"},
                "actor": {"type": "string"},
                "action": {"type": "string"},
                "since_days": {"type": "integer"},
                "limit": {"type": "integer"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "integration_list",
        "description": (
            "List integrations, optionally filtered by connection status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["connected", "error", "disconnected"],
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]


_TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register_tool(
    name: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a tool implementation under a unique name."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if name in _TOOL_REGISTRY:
            raise ToolError(f"Tool already registered: {name}")

        _TOOL_REGISTRY[name] = func
        return func

    return decorator


def get_registered_tools() -> List[str]:
    """Return registered tool names."""
    return list(_TOOL_REGISTRY.keys())


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return schemas only for tools that are currently registered."""
    registered = set(_TOOL_REGISTRY.keys())

    return [
        schema
        for schema in TOOL_SCHEMAS
        if schema["name"] in registered
    ]


def validate_arguments(
    tool_name: str,
    arguments: Dict[str, Any],
) -> None:
    """Validate required and unexpected arguments against the tool schema."""
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object")

    schema = next(
        (item for item in TOOL_SCHEMAS if item["name"] == tool_name),
        None,
    )

    if schema is None:
        raise ValueError(f"No schema defined for tool: {tool_name}")

    parameters = schema.get("parameters", {})
    properties = parameters.get("properties", {})
    required = parameters.get("required", [])

    missing = [key for key in required if key not in arguments]

    if missing:
        raise ValueError(
            f"Missing required arguments for {tool_name}: {', '.join(missing)}"
        )

    unexpected = [
        key for key in arguments
        if key not in properties
    ]

    if unexpected:
        raise ValueError(
            f"Unexpected arguments for {tool_name}: {', '.join(unexpected)}"
        )


def dispatch_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str,
    role: str,
) -> Dict[str, Any]:
    """Authorize, validate, and execute a registered tool."""

    if tool_name not in _TOOL_REGISTRY:
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": f"Unknown tool: {tool_name}",
            "citations": [],
        }

    # Authorize before validation to avoid exposing argument requirements.
    if not is_allowed(role, tool_name):
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": (
                f"Role '{role}' is not permitted to use tool '{tool_name}'"
            ),
            "citations": [],
        }

    try:
        validate_arguments(tool_name, arguments)

        result = _TOOL_REGISTRY[tool_name](
            user_id=user_id,
            **arguments,
        )

        citations = []

        if isinstance(result, dict):
            citations = result.get("citations", [])

        return {
            "tool": tool_name,
            "ok": True,
            "result": result,
            "error": None,
            "citations": citations,
        }

    except Exception as exc:
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": str(exc),
            "citations": [],
        }


# Import after defining the registry and dispatcher. This registers Copilot
# implementations when app.tools is imported directly by tests or other modules.
from app import copilot_tools  # noqa: E402, F401
