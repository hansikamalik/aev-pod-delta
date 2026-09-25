from github_connector.normalization import (
    normalize,
    normalize_alert,
    normalize_findings,
    normalize_repo,
)

REPO = {"id": 10, "full_name": "acme/api", "repository": None}


def repo(**kw):
    base = {
        "id": 10, "full_name": "acme/api", "visibility": "private", "language": "Python",
        "default_branch": "main", "created_at": "2025-01-01T00:00:00Z", "pushed_at": "2026-09-01T00:00:00Z",
    }
    return {**base, **kw}


def alert(kind, **kw):
    return {"_alert_type": kind, "number": 7, "repository": {"id": 10, "full_name": "acme/api"},
            "created_at": "2026-09-05T10:00:00Z", **kw}


def test_repo_maps_to_repository_asset_with_tags():
    a = normalize_repo(repo(archived=True, fork=True))
    assert a.asset_type == "repository" and a.name == "acme/api" and a.external_id == "10"
    assert {"gh-visibility:private", "gh-language:Python", "gh-archived", "gh-fork"} <= set(a.tags)
    assert a.first_seen == "2025-01-01T00:00:00Z" and a.last_seen == "2026-09-01T00:00:00Z"


def test_repo_visibility_falls_back_to_private_flag():
    assert "gh-visibility:public" in normalize_repo({"id": 1, "full_name": "a/b", "private": False}).tags


def test_repo_raw_excludes_alerts():
    assert "alerts" not in normalize_repo({**repo(), "alerts": [1]}).raw


def test_dependabot_finding():
    f = normalize_alert(alert("dependabot",
                              security_advisory={"severity": "critical", "summary": "RCE in lib"},
                              dependency={"package": {"name": "lib"}}))
    assert f.severity == "critical" and f.title == "RCE in lib"
    assert f.external_id == "dependabot:acme/api#7" and f.asset_external_id == "10"
    assert "lib" in f.description and f.detected_at == "2026-09-05T10:00:00Z"


def test_dependabot_moderate_maps_to_medium():
    assert normalize_alert(alert("dependabot", security_advisory={"severity": "moderate"})).severity == "medium"


def test_code_scanning_prefers_security_severity_level():
    f = normalize_alert(alert("code_scanning", rule={"id": "py/sqli", "severity": "warning",
                                                     "security_severity_level": "high", "description": "SQL injection"}))
    assert f.severity == "high" and f.title == "SQL injection"


def test_code_scanning_falls_back_to_rule_severity():
    assert normalize_alert(alert("code_scanning", rule={"id": "x", "severity": "error"})).severity == "high"


def test_secret_scanning_is_high_and_never_carries_secret():
    f = normalize_alert(alert("secret_scanning", secret="ghp_LEAK", secret_type_display_name="GitHub PAT"))
    assert f.severity == "high" and f.title == "GitHub PAT"
    assert "ghp_LEAK" not in str(f)


def test_unknown_alert_type_and_severity_default_safely():
    assert normalize_alert(alert("mystery")).severity == "unknown"
    assert normalize_alert(alert("dependabot")).severity == "unknown"


def test_normalize_skips_orphans_but_findings_keep_them():
    records = [{**repo(), "alerts": [alert("dependabot")]},
               {"_orphaned_alerts": True, "alerts": [alert("dependabot", number=8)]}]
    assert len(normalize(records)) == 1
    assert len(normalize_findings(records)) == 2
