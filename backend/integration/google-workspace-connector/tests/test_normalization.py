from google_workspace_connector.normalization import normalize, normalize_findings

SAMPLE_USER = {
    "id": "user-123",
    "primaryEmail": "jane@customer.com",
    "isAdmin": True,
    "suspended": False,
    "isEnrolledIn2Sv": True,
    "creationTime": "2024-01-01T00:00:00Z",
    "lastLoginTime": "2026-09-01T00:00:00Z",
}

SAMPLE_ACTIVITY = {
    "id": {"uniqueQualifier": "act-1", "time": "2026-09-15T10:00:00Z"},
    "actor": {"email": "admin@customer.com", "profileId": "admin-profile-1"},
    "events": [
        {"name": "GRANT_ADMIN_PRIVILEGE"},
        {"name": "CHANGE_CALENDAR_SETTING"},
    ],
}


def test_normalize_maps_user_fields():
    assets = normalize([SAMPLE_USER])

    assert len(assets) == 1
    asset = assets[0]
    assert asset.external_id == "user-123"
    assert asset.source == "google_workspace"
    assert asset.asset_type == "user"
    assert asset.name == "jane@customer.com"
    assert asset.first_seen == "2024-01-01T00:00:00Z"
    assert asset.last_seen == "2026-09-01T00:00:00Z"
    assert "admin" in asset.tags
    assert "2sv-enrolled" in asset.tags
    assert "suspended" not in asset.tags


def test_normalize_falls_back_to_id_when_no_email():
    assets = normalize([{"id": "user-999"}])

    assert assets[0].name == "user-999"
    assert assets[0].tags == ["2sv-not-enrolled"]


def test_normalize_findings_expands_one_activity_into_multiple_findings():
    findings = normalize_findings([SAMPLE_ACTIVITY])

    assert len(findings) == 2
    assert {f.title for f in findings} == {"GRANT_ADMIN_PRIVILEGE", "CHANGE_CALENDAR_SETTING"}


def test_normalize_findings_severity_split():
    findings = normalize_findings([SAMPLE_ACTIVITY])
    by_title = {f.title: f for f in findings}

    assert by_title["GRANT_ADMIN_PRIVILEGE"].severity == "high"
    assert by_title["CHANGE_CALENDAR_SETTING"].severity == "informational"


def test_normalize_findings_sets_asset_link_and_description():
    findings = normalize_findings([SAMPLE_ACTIVITY])

    finding = findings[0]
    assert finding.asset_external_id == "admin-profile-1"
    assert "admin@customer.com" in finding.description
    assert finding.detected_at == "2026-09-15T10:00:00Z"


def test_normalize_findings_handles_activity_with_no_events():
    findings = normalize_findings([{"id": {}, "actor": {}}])

    # events defaults to [{}] -> one finding with an "unknown_event" title
    assert len(findings) == 1
    assert findings[0].title == "unknown_event"
