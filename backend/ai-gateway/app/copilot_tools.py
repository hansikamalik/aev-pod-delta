
"""Registered Copilot tools for workflows, policies, audits, and integrations."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.tools import register_tool
from app import report_generate   # noqa: F401


_WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "rotate_credentials": {
        "workflow_id": "rotate_credentials",
        "description": "Rotate credentials for a specified asset.",
        "required_params": ["asset_id"],
    },
    "isolate_host": {
        "workflow_id": "isolate_host",
        "description": "Isolate a host from the network.",
        "required_params": ["host_id"],
    },
    "rescan_asset": {
        "workflow_id": "rescan_asset",
        "description": "Run a vulnerability rescan against an asset.",
        "required_params": ["asset_id"],
    },
}

_POLICY_RULES: Dict[str, Dict[str, Any]] = {
    "pol-no-public-access": {
        "resource_types": ["storage_bucket"],
        "field": "public_access",
        "expected": False,
        "description": "Storage buckets must not allow public access.",
    },
    "pol-storage-encryption": {
        "resource_types": ["storage_bucket", "database"],
        "field": "encrypted",
        "expected": True,
        "description": "Stored data must be encrypted.",
    },
    "pol-user-mfa": {
        "resource_types": ["user_account"],
        "field": "mfa_enabled",
        "expected": True,
        "description": "User accounts must have MFA enabled.",
    },
    "pol-firewall-admin-ports": {
        "resource_types": ["firewall_rule"],
        "field": "open_admin_ports",
        "expected": False,
        "description": "Administrative ports must not be openly exposed.",
    },
}

_MOCK_AUDIT_EVENTS: List[Dict[str, Any]] = [
    {
        "resource": "firewall",
        "actor": "hansika",
        "action": "update",
        "details": "Firewall rule updated",
        "days_ago": 2,
    },
    {
        "resource": "storage_bucket",
        "actor": "analyst01",
        "action": "policy_check",
        "details": "Storage bucket policy checked",
        "days_ago": 5,
    },
    {
        "resource": "database",
        "actor": "admin01",
        "action": "read",
        "details": "Database audit event",
        "days_ago": 9,
    },
]

_MOCK_INTEGRATIONS: List[Dict[str, Any]] = [
    {"name": "Microsoft Defender", "status": "connected"},
    {"name": "GitHub", "status": "connected"},
    {"name": "Okta", "status": "error"},
    {"name": "Splunk", "status": "disconnected"},
]


def _start_workflow_run(
    workflow_id: str,
    params: Dict[str, Any],
    user_id: str,
) -> Dict[str, Any]:
    """Mock workflow execution entry point."""
    return {
        "status": "started",
        "run_id": f"run-{workflow_id}-{user_id}",
        "workflow_id": workflow_id,
        "params": params,
        "started_by": user_id,
    }


@register_tool("workflow_assist")
def workflow_assist(
    user_id: str,
    action: str,
    workflow_id: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """List, describe, dry-run, or start a supported workflow."""
    if action == "list":
        return {
            "workflows": list(_WORKFLOWS.values()),
            "count": len(_WORKFLOWS),
        }

    if action == "describe":
        if not workflow_id:
            raise ValueError("workflow_id is required for describe")

        workflow = _WORKFLOWS.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Unknown workflow_id: {workflow_id}")

        return {"workflow": workflow}

    if action == "run":
        if not workflow_id:
            raise ValueError("workflow_id is required for run")

        workflow = _WORKFLOWS.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Unknown workflow_id: {workflow_id}")

        run_params = params or {}
        missing = [
            name
            for name in workflow["required_params"]
            if name not in run_params or run_params[name] in (None, "")
        ]

        if missing:
            raise ValueError(
                f"Missing required workflow parameters: {', '.join(missing)}"
            )

        if dry_run:
            return {
                "status": "dry_run",
                "workflow_id": workflow_id,
                "params": run_params,
                "started_by": user_id,
            }

        return _start_workflow_run(workflow_id, run_params, user_id)

    raise ValueError(f"Unsupported workflow action: {action}")


@register_tool("policy_check")
def policy_check(
    user_id: str,
    resource_type: str,
    config: Dict[str, Any],
    policy_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluate a resource configuration against supported policy rules."""
    del user_id

    if not isinstance(config, dict):
        raise ValueError("config must be an object")

    if policy_ids is not None:
        unknown_ids = [
            policy_id for policy_id in policy_ids
            if policy_id not in _POLICY_RULES
        ]
        if unknown_ids:
            raise ValueError(f"Unknown policy IDs: {', '.join(unknown_ids)}")
        selected_ids = policy_ids
    else:
        selected_ids = list(_POLICY_RULES.keys())

    applicable = []
    violations = []

    for policy_id in selected_ids:
        rule = _POLICY_RULES[policy_id]
        if resource_type not in rule["resource_types"]:
            continue

        applicable.append(policy_id)
        field = rule["field"]

        if field not in config:
            continue

        actual = config[field]
        expected = rule["expected"]

        if actual != expected:
            violations.append(
                {
                    "policy_id": policy_id,
                    "field": field,
                    "actual": actual,
                    "expected": expected,
                    "description": rule["description"],
                }
            )

    if not applicable:
        raise ValueError(
            f"No applicable policies found for resource_type: {resource_type}"
        )

    return {
        "resource_type": resource_type,
        "compliant": len(violations) == 0,
        "policies_checked": applicable,
        "violations": violations,
        "violation_count": len(violations),
    }


@register_tool("audit_query")
def audit_query(
    user_id: str,
    resource: Optional[str] = None,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    since_days: int = 7,
    limit: int = 50,
) -> Dict[str, Any]:
    """Query mock audit events using optional filters."""
    if not isinstance(since_days, int) or not 1 <= since_days <= 90:
        raise ValueError("since_days must be an integer between 1 and 90")

    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("limit must be an integer between 1 and 200")

    now = datetime.now(timezone.utc)
    entries: List[Dict[str, Any]] = []

    for event in _MOCK_AUDIT_EVENTS:
        if event["days_ago"] > since_days:
            continue
        if resource is not None and event["resource"] != resource:
            continue
        if actor is not None and event["actor"] != actor:
            continue
        if action is not None and event["action"] != action:
            continue

        entries.append(
            {
                "resource": event["resource"],
                "actor": event["actor"],
                "action": event["action"],
                "details": event["details"],
                "timestamp": (
                    now - timedelta(days=event["days_ago"])
                ).isoformat(),
            }
        )

    entries = entries[:limit]

    return {
        "count": len(entries),
        "entries": entries,
        "queried_by": user_id,
        "since_days": since_days,
        "limit": limit,
    }


@register_tool("integration_list")
def integration_list(
    user_id: str,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List integrations, optionally filtered by connection status."""
    del user_id

    valid_statuses = {"connected", "error", "disconnected"}
    if status is not None and status not in valid_statuses:
        raise ValueError(
            "status must be one of: connected, error, disconnected"
        )

    integrations = [
        integration.copy()
        for integration in _MOCK_INTEGRATIONS
        if status is None or integration["status"] == status
    ]

    return {
        "count": len(integrations),
        "integrations": integrations,
    }
