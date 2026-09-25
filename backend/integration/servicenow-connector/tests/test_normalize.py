from connectors.servicenow.normalize import normalize_ci, normalize_incident


def test_normalize_ci_minimal():
    rec = {"sys_id": "abc123", "name": "srv-01", "sys_class_name": "cmdb_ci_server",
           "ip_address": "10.0.0.1, 10.0.0.2", "fqdn": "srv-01.corp.local",
           "os": "Ubuntu 22.04", "sys_created_on": "2026-09-01 10:00:00"}
    asset = normalize_ci(rec)
    assert asset["asset_id"] == "servicenow:abc123"
    assert asset["type"] == "server"
    assert asset["ip_addresses"] == ["10.0.0.1", "10.0.0.2"]
    assert asset["fqdn"] == "srv-01.corp.local"
    assert asset["source"] == "servicenow"
    assert asset["raw"] is rec


def test_normalize_ci_defaults():
    asset = normalize_ci({"sys_id": "x"})
    assert asset["name"] == "x"
    assert asset["type"] == "unknown"
    assert asset["ip_addresses"] == []


def test_normalize_incident_severity_mapping():
    rec = {"sys_id": "inc1", "severity": "1", "short_description": "Critical vuln",
           "state": "Open", "cmdb_ci": "abc123", "opened_at": "2026-09-02 08:00:00"}
    f = normalize_incident(rec)
    assert f["finding_id"] == "servicenow:inc1"
    assert f["asset_id"] == "servicenow:abc123"
    assert f["severity"] == "critical"
    assert f["status"] == "open"


def test_normalize_incident_reference_dict():
    rec = {"sys_id": "inc2", "impact": "3", "cmdb_ci": {"value": "zz9"}}
    f = normalize_incident(rec)
    assert f["asset_id"] == "servicenow:zz9"
    assert f["severity"] == "medium"


def test_normalize_incident_unknown_severity_defaults_info():
    f = normalize_incident({"sys_id": "inc3", "severity": "9"})
    assert f["severity"] == "info"
