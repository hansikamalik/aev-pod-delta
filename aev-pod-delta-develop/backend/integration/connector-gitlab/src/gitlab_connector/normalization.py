"""
Normalization: map GitLab project/vulnerability shapes to the shared
Asset/Finding shape used across all connectors.

Est: 0.5 day (per plan's per-connector standard pattern)
"""

from typing import Any, Dict, List

from .base import Asset, Finding

SOURCE = "gitlab"

# NOTE: mirrors the GitHub connector (critical preserved; other connectors use
# high/medium/low/info/unknown). Confirm with the platform team.
SEVERITY_MAP = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "info",
    "unknown": "unknown",
    "undefined": "unknown",
}

SENSITIVE_KEYS = ("raw_source_code_extract",)


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items() if k not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def normalize_project(project: Dict[str, Any]) -> Asset:
    tags: List[str] = []
    if project.get("visibility"):
        tags.append(f"gl-visibility:{project['visibility']}")
    if project.get("default_branch"):
        tags.append(f"gl-default-branch:{project['default_branch']}")
    if project.get("archived"):
        tags.append("gl-archived")
    if project.get("forked_from_project"):
        tags.append("gl-fork")

    return Asset(
        external_id=str(project.get("id", "")),
        source=SOURCE,
        asset_type="repository",
        name=project.get("path_with_namespace") or project.get("name") or "unnamed-project",
        raw={k: v for k, v in project.items() if k != "vulnerabilities"},
        tags=tags,
        first_seen=project.get("created_at"),
        last_seen=project.get("last_activity_at"),
    )


def normalize_vulnerability(vuln: Dict[str, Any], project: Dict[str, Any]) -> Finding:
    project_path = project.get("path_with_namespace") or project.get("name") or "unknown"
    report_type = vuln.get("report_type", "unknown")
    severity = SEVERITY_MAP.get(str(vuln.get("severity") or "").lower(), "unknown")

    return Finding(
        external_id=f"vulnerability:{project_path}#{vuln.get('id')}",
        source=SOURCE,
        severity=severity,
        title=vuln.get("title") or "GitLab vulnerability",
        description=(
            f"{report_type} finding in {project_path} "
            f"(state: {vuln.get('state', 'unknown')}). {vuln.get('description') or ''}"
        ).strip(),
        asset_external_id=str(project["id"]) if project.get("id") is not None else None,
        raw=_scrub(vuln),
        detected_at=vuln.get("detected_at") or vuln.get("created_at"),
    )


def normalize_findings(raw_records: List[Dict[str, Any]]) -> List[Finding]:
    return [normalize_vulnerability(v, r) for r in raw_records for v in r.get("vulnerabilities", [])]


def normalize(raw_records: List[Dict[str, Any]]) -> List[Asset]:
    """Connector ABC entry point: projects -> Assets."""
    return [normalize_project(r) for r in raw_records]
