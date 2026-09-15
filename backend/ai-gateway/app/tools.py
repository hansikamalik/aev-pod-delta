"""
Tool-calling framework for the AI Gateway.

This module does two things:

1. Defines the SCHEMA for every tool the Copilot is allowed to call.
   The schema is what gets sent to Gemma so it knows which tools exist,
   what each one does, and what arguments each one needs.

2. Provides the DISPATCHER, which takes a tool name requested by the
   model and routes it to the real Python function that implements it.

Individual tool implementations (asset_search, exposure_query, etc.)
are registered here by the squad members who build them. This module
only owns the framework -- not the tool logic itself.
"""

from app.permissions import is_allowed
from typing import Any, Callable, Dict, List


class ToolError(Exception):
    """Raised when a tool cannot be dispatched or fails validation."""


# ---------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------
# Each entry describes one tool in the format an LLM expects:
#   name        -- what the model calls it by
#   description -- tells the model WHEN to use this tool
#   parameters  -- JSON Schema describing the arguments
#
# Keep descriptions specific. A vague description is the most common
# reason a model picks the wrong tool.

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "asset_search",
        "description": (
            "Search the platform's asset inventory using a natural-language "
            "description. Use when the user is looking for assets but does "
            "not know the exact name or ID."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language description of the asset.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "exposure_query",
        "description": (
            "Look up security exposures (vulnerabilities, misconfigurations) "
            "for the organisation, optionally filtered by asset or severity."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Optional asset ID to filter exposures by.",
                },
                "severity": {
                    "type": "string",
                    "description": "Optional severity filter.",
                    "enum": ["low", "medium", "high", "critical"],
                },
            },
            "required": [],
        },
    },
    {
        "name": "risk_score_get",
        "description": (
            "Get the current calculated risk score for a specific asset. "
            "Use when the user asks how risky a named asset is."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "The asset ID to get the risk score for.",
                },
            },
            "required": ["asset_id"],
        },
    },
]


# ---------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------
# Maps a tool name to the Python function that implements it.
# Squad members register their tool here via @register_tool.

_TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {}


def register_tool(name: str) -> Callable:
    """
    Decorator that registers a function as the implementation of a tool.

    Usage:
        @register_tool("risk_score_get")
        def risk_score_get(asset_id: str, user_id: str) -> dict:
            ...

    Every tool function MUST accept a `user_id` keyword argument so the
    dispatcher can enforce per-user permissions on the call.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if name in _TOOL_REGISTRY:
            raise ToolError(f"Tool '{name}' is already registered.")
        _TOOL_REGISTRY[name] = func
        return func

    return decorator


def get_registered_tools() -> List[str]:
    """Return the names of every tool that has an implementation."""

    return sorted(_TOOL_REGISTRY.keys())


def get_tool_schemas() -> List[Dict[str, Any]]:
    """
    Return the schemas for tools that actually have an implementation.

    A tool with a schema but no registered function is not advertised to
    the model -- otherwise the model could request something that cannot
    be dispatched.
    """

    return [
        schema
        for schema in TOOL_SCHEMAS
        if schema["name"] in _TOOL_REGISTRY
    ]


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def _get_schema(tool_name: str) -> Dict[str, Any]:
    for schema in TOOL_SCHEMAS:
        if schema["name"] == tool_name:
            return schema
    raise ToolError(f"Unknown tool: '{tool_name}'")


def validate_arguments(tool_name: str, arguments: Dict[str, Any]) -> None:
    """
    Check the model's requested arguments against the tool's schema.

    Raises ToolError when a required argument is missing or an unexpected
    argument is supplied. This matters because the arguments come from an
    LLM, not from trusted code -- they cannot be assumed well-formed.
    """

    schema = _get_schema(tool_name)
    params = schema.get("parameters", {})
    properties = params.get("properties", {})
    required = params.get("required", [])

    missing = [key for key in required if key not in arguments]
    if missing:
        raise ToolError(
            f"Tool '{tool_name}' missing required argument(s): "
            f"{', '.join(missing)}"
        )

    unexpected = [key for key in arguments if key not in properties]
    if unexpected:
        raise ToolError(
            f"Tool '{tool_name}' received unexpected argument(s): "
            f"{', '.join(unexpected)}"
        )


# ---------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------

def dispatch_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str,
    role: str,
) -> Dict[str, Any]:
    """
    Route a model-requested tool call to its implementation and run it.

    Returns a normalised envelope so the caller always gets the same
    shape back, whether the tool succeeded or failed:

        {"tool": str, "ok": bool, "result": Any, "error": str | None}

    A failing tool must not crash the whole request -- the model needs a
    chance to explain the failure to the user instead.

    RBAC is enforced here, centrally, rather than inside each tool --
    that way no tool implementation can forget the permission check.
    The check runs BEFORE argument validation on purpose: a caller who
    lacks permission for a tool should not learn anything about that
    tool's expected arguments either.
    """

    if tool_name not in _TOOL_REGISTRY:
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": f"Unknown or unregistered tool: '{tool_name}'",
        }

    if not is_allowed(role, tool_name):
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": f"Role '{role}' is not permitted to use '{tool_name}'.",
        }

    try:
        validate_arguments(tool_name, arguments)
    except ToolError as exc:
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": str(exc),
        }

    func = _TOOL_REGISTRY[tool_name]

    try:
        # user_id is always passed so the tool can scope its query to
        # what this specific caller is allowed to see (defense in depth
        # on top of the role check above).
        result = func(user_id=user_id, **arguments)
    except Exception as exc:  # noqa: BLE001 - tools are third-party code
        return {
            "tool": tool_name,
            "ok": False,
            "result": None,
            "error": f"Tool '{tool_name}' failed: {exc}",
        }

    return {
        "tool": tool_name,
        "ok": True,
        "result": result,
        "error": None,
    }
