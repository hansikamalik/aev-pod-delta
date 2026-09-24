from microsoft_defender_connector.normalization import normalize_alert, normalize_machine


def test_normalize_machine_maps_core_fields():
    raw = {
        "id": "m1",
        "computerDnsName": "host-1.corp.local",
        "osPlatform": "Windows10",
        "version": "21H2",
        "healthStatus": "Active",
        "riskScore": "High",
        "exposureLevel": "Medium",
        "lastSeen": "2026-09-20T10:00:00Z",
        "ipAddresses": [{"ipAddress": "10.0.0.5"}],
        "onboardingStatus": "Onboarded",
        "rbacGroupName": "corp-endpoints",
    }

    asset = normalize_machine(raw)

    assert asset.external_id == "m1"
    assert asset.name == "host-1.corp.local"
    assert asset.type == "endpoint"
    assert asset.attributes["risk_score"] == "High"
    assert asset.tags == {"source": "microsoft_defender", "machine_group": "corp-endpoints"}


def test_normalize_machine_falls_back_to_id_when_no_dns_name():
    raw = {"id": "m2"}
    asset = normalize_machine(raw)
    assert asset.name == "m2"


def test_normalize_alert_maps_severity_and_links_asset():
    raw = {
        "id": "a1",
        "machineId": "m1",
        "title": "Suspicious PowerShell command",
        "severity": "High",
        "status": "New",
        "category": "Execution",
        "description": "Encoded PowerShell command detected.",
    }

    finding = normalize_alert(raw)

    assert finding.external_id == "a1"
    assert finding.asset_external_id == "m1"
    assert finding.severity == "high"
    assert finding.raw == raw


def test_normalize_alert_unknown_severity_maps_to_unknown():
    raw = {"id": "a2", "severity": "SomethingNew"}
    finding = normalize_alert(raw)
    assert finding.severity == "unknown"
