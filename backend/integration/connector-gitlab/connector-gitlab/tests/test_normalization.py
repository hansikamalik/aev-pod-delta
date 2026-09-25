from gitlab_connector.normalization import (
    normalize,
    normalize_findings,
    normalize_project,
    normalize_vulnerability,
)


def project(**kw):
    base = {
        "id": 10, "path_with_namespace": "acme/platform/api", "visibility": "private",
        "default_branch": "main", "created_at": "2025-01-01T00:00:00Z",
        "last_activity_at": "2026-09-01T00:00:00Z",
    }
    return {**base, **kw}


def vuln(**kw):
    return {"id": 5, "title": "SQL injection", "severity": "high", "state": "detected",
            "report_type": "sast", "detected_at": "2026-09-05T10:00:00Z", **kw}


def test_project_maps_to_repository_asset_with_tags():
    a = normalize_project(project(archived=True, forked_from_project={"id": 1}))
    assert a.asset_type == "repository" and a.name == "acme/platform/api" and a.external_id == "10"
    assert {"gl-visibility:private", "gl-default-branch:main", "gl-archived", "gl-fork"} <= set(a.tags)
    assert a.first_seen == "2025-01-01T00:00:00Z" and a.last_seen == "2026-09-01T00:00:00Z"


def test_project_raw_excludes_vulnerabilities():
    assert "vulnerabilities" not in normalize_project({**project(), "vulnerabilities": [1]}).raw


def test_project_name_fallback():
    assert normalize_project({"id": 1}).name == "unnamed-project"


def test_vulnerability_finding_fields():
    f = normalize_vulnerability(vuln(), project())
    assert f.severity == "high" and f.title == "SQL injection"
    assert f.external_id == "vulnerability:acme/platform/api#5"
    assert f.asset_external_id == "10" and f.detected_at == "2026-09-05T10:00:00Z"
    assert "sast" in f.description


def test_severity_mapping_and_defaults():
    p = project()
    assert normalize_vulnerability(vuln(severity="critical"), p).severity == "critical"
    assert normalize_vulnerability(vuln(severity="info"), p).severity == "info"
    assert normalize_vulnerability(vuln(severity="undefined"), p).severity == "unknown"
    assert normalize_vulnerability(vuln(severity=None), p).severity == "unknown"


def test_detected_at_falls_back_to_created_at():
    v = vuln(created_at="2026-09-04T00:00:00Z")
    del v["detected_at"]
    assert normalize_vulnerability(v, project()).detected_at == "2026-09-04T00:00:00Z"


def test_finding_raw_never_contains_source_extract():
    f = normalize_vulnerability(vuln(raw_source_code_extract="LEAK", finding={"raw_source_code_extract": "LEAK"}), project())
    assert "LEAK" not in str(f)


def test_normalize_and_findings_over_records():
    records = [{**project(), "vulnerabilities": [vuln(), vuln(id=6)]}, {**project(id=11, path_with_namespace="acme/web"), "vulnerabilities": []}]
    assert len(normalize(records)) == 2
    assert len(normalize_findings(records)) == 2
