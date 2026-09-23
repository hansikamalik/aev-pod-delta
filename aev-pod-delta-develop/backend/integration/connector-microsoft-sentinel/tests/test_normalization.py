from sentinel_connector.normalization import normalize, normalize_incident


def sample_incident():
    return {
        "name": "incident-1",
        "properties": {
            "severity": "High",
            "title": "Suspicious sign-in",
            "description": "Impossible travel detected",
            "createdTimeUtc": "2026-09-05T10:00:00Z",
        },
        "entities": [
            {"kind": "host", "name": "entity-1", "properties": {"hostName": "web-01"}},
            {"kind": "account", "name": "entity-2", "properties": {"accountName": "jdoe"}},
            {"kind": "unknown_kind", "name": "entity-3", "properties": {}},
        ],
    }


def test_normalize_incident_maps_fields():
    finding = normalize_incident(sample_incident())
    assert finding.external_id == "incident-1"
    assert finding.severity == "high"
    assert finding.title == "Suspicious sign-in"
    assert finding.source == "microsoft_sentinel"


def test_normalize_unknown_severity_maps_to_unknown():
    incident = sample_incident()
    incident["properties"]["severity"] = "Weird"
    finding = normalize_incident(incident)
    assert finding.severity == "unknown"


def test_normalize_entities_to_assets():
    assets = normalize([sample_incident()])
    assert len(assets) == 3

    host_asset = next(a for a in assets if a.asset_type == "endpoint")
    assert host_asset.name == "web-01"

    identity_asset = next(a for a in assets if a.asset_type == "identity")
    assert identity_asset.name == "jdoe"

    unknown_asset = next(a for a in assets if a.asset_type == "unknown")
    assert unknown_asset.external_id == "entity-3"


def test_normalize_empty_records_returns_empty_list():
    assert normalize([]) == []
