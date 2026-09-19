import pytest

from connectors.servicenow.connector import ServiceNowConnector


def _config():
    return {
        "instance_url": "https://x.service-now.com",
        "auth": {"method": "basic", "username": "u", "password": "p"},
        "vault": {"enabled": False},
        "tables": {"cmdb_ci": "cmdb_ci", "incident": "incident"},
        "push": {"asset_url": "https://a/assets", "exposure_url": "https://a/exposures"},
        "batch_size": 200,
    }


def test_normalize_routes_both_shapes():
    conn = ServiceNowConnector(config=_config())
    raw_assets = iter([{"sys_id": "a1", "name": "srv"}])
    raw_findings = iter([{"sys_id": "i1", "severity": "2", "cmdb_ci": "a1"}])
    out = list(conn.normalize((raw_assets, raw_findings)))
    assert out[0]["asset_id"] == "servicenow:a1"
    assert out[1]["finding_id"] == "servicenow:i1"


class _Pusher:
    def __init__(self):
        self.assets, self.findings = [], []

    def push_assets(self, it):
        self.assets = list(it)
        return {"sent": len(self.assets), "accepted": len(self.assets), "failed": 0}

    def push_findings(self, it):
        self.findings = list(it)
        return {"sent": len(self.findings), "accepted": len(self.findings), "failed": 0}


def test_push_splits_assets_and_findings(monkeypatch):
    conn = ServiceNowConnector(config=_config())
    pusher = _Pusher()
    monkeypatch.setattr(conn, "_require_pusher", lambda: pusher)
    records = [
        {"asset_id": "servicenow:a1", "name": "srv"},
        {"finding_id": "servicenow:i1", "title": "t", "asset_id": "servicenow:a1"},
    ]
    stats = conn.push(iter(records))
    assert len(pusher.assets) == 1 and len(pusher.findings) == 1
    assert stats["assets"]["accepted"] == 1 and stats["findings"]["accepted"] == 1


def test_authenticate_env_override(monkeypatch):
    cfg = _config()
    cfg["auth"]["username"] = ""
    monkeypatch.setenv("SN_USERNAME", "env-user")
    monkeypatch.setenv("SN_PASSWORD", "env-pass")
    conn = ServiceNowConnector(config=cfg)
    auth = conn.authenticate()
    assert auth.username == "env-user"
