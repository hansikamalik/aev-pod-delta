"""
Copilot tool implementations.

Every tool takes `user_id` first (the dispatcher injects it, the model never
supplies it) and returns a plain JSON-serialisable dict. The dispatcher wraps
that dict in the standard {"ok", "result", "error"} envelope, and turns any
exception (ValueError for bad input, anything else for backend failures) into
the "error" field, so tools just raise.

The data sources below (_WORKFLOWS, _POLICIES, _audit_events, _INTEGRATIONS)
are stand-ins. Each is isolated behind one small function/constant so you can
swap in your real audit store, integration service, and workflow engine
without touching the tool logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------
# workflow_assist
# ---------------------------------------------------------

_WORKFLOWS = {
    "rotate_credentials": {
        "description": "Rotate credentials for an asset and update dependent secrets.",
        "required_params": ["asset_id"],
        "steps": ["Generate new credentials", "Update secret store", "Restart dependents", "Revoke old credentials"],
    },
    "isolate_host": {
        "description": "Quarantine a host from the network pending investigation.",
        "required_params": ["host_id"],
        "steps": ["Snapshot host state", "Apply quarantine network policy", "Notify on-call"],
    },
    "rescan_asset": {
        "description": "Trigger a fresh vulnerability scan of an asset.",
        "required_params": ["asset_id"],
        "steps": ["Queue scan", "Collect findings", "Update risk score"],
    },
}


def _start_workflow_run(workflow_id: str, params: dict, started_by: str) -> str:
    """Seam: call your real workflow engine here and return its run id."""
    return f"run-{uuid.uuid4().hex[:8]}"


def workflow_assist(user_id, action, workflow_id=None, params=None, dry_run=True):
    if action == "list":
        return {
            "workflows": [
                {"workflow_id": wid, "description": w["description"], "required_params": w["required_params"]}
                for wid, w in _WORKFLOWS.items()
            ]
        }

    if not workflow_id:
        raise ValueError(f"workflow_id is required for action '{action}'")
    workflow = _WORKFLOWS.get(workflow_id)
    if workflow is None:
        raise ValueError(f"Unknown workflow '{workflow_id}'. Available: {sorted(_WORKFLOWS)}")

    if action == "describe":
        return {"workflow_id": workflow_id, **workflow}

    if action == "run":
        params = params or {}
        missing = [p for p in workflow["required_params"] if p not in params]
        if missing:
            raise ValueError(f"Missing workflow parameter(s): {', '.join(missing)}")

        if dry_run:
            # Default is a dry run so the copilot has to be explicit (and
            # ideally get user confirmation) before anything really executes.
            return {
                "status": "dry_run",
                "workflow_id": workflow_id,
                "params": params,
                "would_execute": workflow["steps"],
            }

        run_id = _start_workflow_run(workflow_id, params, started_by=user_id)
        return {
            "status": "started",
            "run_id": run_id,
            "workflow_id": workflow_id,
            "params": params,
            "started_by": user_id,
        }

    raise ValueError(f"Unknown action '{action}'. Use list, describe, or run.")


# ---------------------------------------------------------
# policy_check
# ---------------------------------------------------------

def _public_access(cfg):
    return "public access is enabled" if cfg.get("public_access") is True else None


def _unencrypted(cfg):
    return "encryption at rest is not enabled" if cfg.get("encrypted") is not True else None


def _no_mfa(cfg):
    return "MFA is not enabled" if cfg.get("mfa_enabled") is not True else None


def _open_admin_port(cfg):
    if cfg.get("port") in (22, 3389) and cfg.get("source") == "0.0.0.0/0":
        return f"admin port {cfg['port']} is open to the internet"
    return None


_POLICIES = {
    "pol-no-public-access": {
        "description": "Storage and databases must not be publicly accessible.",
        "severity": "high",
        "applies_to": {"storage_bucket", "database"},
        "check": _public_access,
    },
    "pol-encryption-at-rest": {
        "description": "Storage and databases must be encrypted at rest.",
        "severity": "medium",
        "applies_to": {"storage_bucket", "database"},
        "check": _unencrypted,
    },
    "pol-mfa-required": {
        "description": "All user accounts must have MFA enabled.",
        "severity": "high",
        "applies_to": {"user_account"},
        "check": _no_mfa,
    },
    "pol-no-open-admin-ports": {
        "description": "SSH/RDP must not be open to 0.0.0.0/0.",
        "severity": "critical",
        "applies_to": {"firewall_rule"},
        "check": _open_admin_port,
    },
}


def policy_check(user_id, resource_type, config, policy_ids=None):
    if not isinstance(config, dict):
        raise ValueError("config must be an object")

    if policy_ids:
        unknown = [p for p in policy_ids if p not in _POLICIES]
        if unknown:
            raise ValueError(f"Unknown policy id(s): {', '.join(unknown)}")
        candidates = policy_ids
    else:
        candidates = list(_POLICIES)

    applicable = [p for p in candidates if resource_type in _POLICIES[p]["applies_to"]]
    if not applicable:
        raise ValueError(f"No policies apply to resource_type '{resource_type}'")

    violations = []
    for pid in applicable:
        policy = _POLICIES[pid]
        detail = policy["check"](config)
        if detail:
            violations.append(
                {
                    "policy_id": pid,
                    "severity": policy["severity"],
                    "description": policy["description"],
                    "detail": detail,
                }
            )

    return {
        "resource_type": resource_type,
        "compliant": not violations,
        "policies_evaluated": applicable,
        "violations": violations,
    }


# ---------------------------------------------------------
# audit_query
# ---------------------------------------------------------

def _audit_events():
    """Seam: replace with a query against your real audit store."""
    now = datetime.now(timezone.utc)
    return [
        {"timestamp": now - timedelta(days=2), "actor": "hansika", "action": "config.update",
         "resource": "firewall/prod-edge", "detail": "Opened port 443 to partner range"},
        {"timestamp": now - timedelta(days=5), "actor": "svc-deploy", "action": "config.update",
         "resource": "db-prod-01/backup-policy", "detail": "Retention 30d -> 14d"},
        {"timestamp": now - timedelta(days=9), "actor": "someone", "action": "role.grant",
         "resource": "user/someone", "detail": "Granted analyst role"},
    ]


def audit_query(user_id, resource=None, actor=None, action=None, since_days=7, limit=50):
    if not 1 <= since_days <= 90:
        raise ValueError("since_days must be between 1 and 90")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")

    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    matches = [
        e for e in _audit_events()
        if e["timestamp"] >= cutoff
        and (resource is None or resource.lower() in e["resource"].lower())
        and (actor is None or e["actor"] == actor)
        and (action is None or e["action"] == action)
    ]
    matches.sort(key=lambda e: e["timestamp"], reverse=True)

    entries = [{**e, "timestamp": e["timestamp"].isoformat()} for e in matches[:limit]]
    return {
        "window_days": since_days,
        "count": len(entries),
        "truncated": len(matches) > limit,
        "entries": entries,
    }


# ---------------------------------------------------------
# integration_list
# ---------------------------------------------------------

# Deliberately excludes credentials/tokens: the model should only ever see
# names and health, never secrets.
_INTEGRATIONS = [
    {"name": "Microsoft Defender", "category": "endpoint_security", "status": "connected", "last_sync": "2026-09-29T08:12:00Z"},
    {"name": "GitHub", "category": "source_control", "status": "connected", "last_sync": "2026-09-29T09:01:00Z"},
    {"name": "Okta", "category": "identity", "status": "error", "last_sync": "2026-09-27T22:40:00Z"},
    {"name": "Splunk", "category": "siem", "status": "disconnected", "last_sync": None},
]


def integration_list(user_id, status=None):
    items = [i for i in _INTEGRATIONS if status is None or i["status"] == status]
    return {"count": len(items), "integrations": [dict(i) for i in items]}
