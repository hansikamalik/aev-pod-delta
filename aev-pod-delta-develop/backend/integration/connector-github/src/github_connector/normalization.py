"""
Normalization: map GitHub repository/alert shapes to the shared
Asset/Finding shape used across all connectors.

Est: 0.5 day (per plan's per-connector standard pattern)
"""

from typing import Any, Dict, List

from .base import Asset, Finding

SOURCE = "github"

# NOTE: the other connectors use high/medium/low/info/unknown. GitHub has a
# real "critical" level; it is preserved here. Confirm with the platform team.
SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "moderate": "medium",
    "low": "low",
    "error": "high",      # code scanning legacy rule.severity
    "warning": "medium",
    "note": "low",
}

SENSITIVE_KEYS = ("secret",)


def _sev(value: Any) -> str:
    return SEVERITY_MAP.get(str(value or "").lower(), "unknown")


def normalize_repo(repo: Dict[str, Any]) -> Asset:
    tags: List[str] = []
    if repo.get("visibility"):
        tags.append(f"gh-visibility:{repo['visibility']}")
    elif "private" in repo:
        tags.append("gh-visibility:private" if repo["private"] else "gh-visibility:public")
    if repo.get("language"):
        tags.append(f"gh-language:{repo['language']}")
    if repo.get("default_branch"):
        tags.append(f"gh-default-branch:{repo['default_branch']}")
    if repo.get("archived"):
        tags.append("gh-archived")
    if repo.get("fork"):
        tags.append("gh-fork")

    return Asset(
        external_id=str(repo.get("id", "")),
        source=SOURCE,
        asset_type="repository",
        name=repo.get("full_name") or repo.get("name") or "unnamed-repo",
        raw={k: v for k, v in repo.items() if k != "alerts"},
        tags=tags,
        first_seen=repo.get("created_at"),
        last_seen=repo.get("pushed_at") or repo.get("updated_at"),
    )


def normalize_alert(alert: Dict[str, Any]) -> Finding:
    kind = alert.get("_alert_type", "unknown")
    repo = alert.get("repository") or {}
    repo_name = repo.get("full_name", "unknown")
    number = alert.get("number")
    raw = {k: v for k, v in alert.items() if k not in SENSITIVE_KEYS}

    if kind == "dependabot":
        adv = alert.get("security_advisory") or {}
        pkg = ((alert.get("dependency") or {}).get("package") or {}).get("name", "unknown package")
        severity = _sev(adv.get("severity"))
        title = adv.get("summary") or "Dependabot alert"
        description = f"Vulnerable dependency {pkg} in {repo_name}"
    elif kind == "code_scanning":
        rule = alert.get("rule") or {}
        severity = _sev(rule.get("security_severity_level") or rule.get("severity"))
        title = rule.get("description") or rule.get("id") or "Code scanning alert"
        path = ((alert.get("most_recent_instance") or {}).get("location") or {}).get("path", "unknown file")
        description = f"{rule.get('id', 'rule')} in {repo_name}: {path}"
    elif kind == "secret_scanning":
        severity = "high"  # exposed credentials; GitHub provides no severity field
        title = alert.get("secret_type_display_name") or alert.get("secret_type") or "Exposed secret"
        description = f"Exposed secret in {repo_name} (validity: {alert.get('validity', 'unknown')})"
    else:
        severity, title, description = "unknown", "GitHub alert", f"Alert in {repo_name}"

    return Finding(
        external_id=f"{kind}:{repo_name}#{number}",
        source=SOURCE,
        severity=severity,
        title=title,
        description=description,
        asset_external_id=str(repo["id"]) if repo.get("id") is not None else None,
        raw=raw,
        detected_at=alert.get("created_at"),
    )


def normalize_findings(raw_records: List[Dict[str, Any]]) -> List[Finding]:
    return [normalize_alert(a) for r in raw_records for a in r.get("alerts", [])]


def normalize(raw_records: List[Dict[str, Any]]) -> List[Asset]:
    """Connector ABC entry point: repositories -> Assets (orphan-alert records skipped)."""
    return [normalize_repo(r) for r in raw_records if not r.get("_orphaned_alerts")]
