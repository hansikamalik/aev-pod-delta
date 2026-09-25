from sentinelone_connector.normalization import (
    normalize,
    normalize_agent,
    normalize_findings,
    normalize_threat,
)


def agent(**kw):
    base = {
        "id": "a1", "computerName": "web-01", "machineType": "server", "osType": "linux",
        "siteName": "HQ", "groupName": "prod", "agentVersion": "23.4",
        "createdAt": "2026-01-01T00:00:00Z", "lastActiveDate": "2026-09-05T00:00:00Z",
    }
    return {**base, **kw}


def threat(confidence="malicious"):
    return {
        "id": "t1",
        "threatInfo": {
            "threatName": "evil.exe", "classification": "Trojan", "confidenceLevel": confidence,
            "incidentStatus": "unresolved", "mitigationStatus": "not_mitigated",
            "identifiedAt": "2026-09-05T10:00:00Z",
        },
        "agentRealtimeInfo": {"agentId": "a1"},
    }


def test_agent_maps_server_type_and_tags():
    a = normalize_agent(agent())
    assert a.asset_type == "server"
    assert a.name == "web-01"
    assert "s1-os:linux" in a.tags and "s1-site:HQ" in a.tags
    assert a.first_seen == "2026-01-01T00:00:00Z"


def test_agent_flags_infected_and_decommissioned():
    a = normalize_agent(agent(infected=True, isDecommissioned=True))
    assert "s1-infected" in a.tags and "s1-decommissioned" in a.tags


def test_agent_unknown_machine_type_defaults_to_endpoint():
    assert normalize_agent(agent(machineType="weird")).asset_type == "endpoint"


def test_agent_missing_name_falls_back():
    assert normalize_agent(agent(computerName=None)).name == "unnamed-agent"


def test_threat_severity_mapping():
    assert normalize_threat(threat("malicious")).severity == "high"
    assert normalize_threat(threat("suspicious")).severity == "medium"
    assert normalize_threat(threat("n/a")).severity == "low"


def test_threat_links_to_agent_and_has_timestamp():
    f = normalize_threat(threat())
    assert f.asset_external_id == "a1"
    assert f.detected_at == "2026-09-05T10:00:00Z"
    assert f.title == "evil.exe"


def test_normalize_skips_orphan_records_but_findings_keep_them():
    records = [{**agent(), "threats": [threat()]}, {"_orphaned_threats": True, "threats": [threat()]}]
    assert len(normalize(records)) == 1
    assert len(normalize_findings(records)) == 2


def test_asset_raw_excludes_threats_key():
    a = normalize_agent({**agent(), "threats": [threat()]})
    assert "threats" not in a.raw
