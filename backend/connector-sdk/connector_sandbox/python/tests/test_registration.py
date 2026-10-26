"""
Demo + test suite for POST /connectors/custom. Run this to see the whole
thing work end to end with zero real infrastructure:

    pytest tests/test_registration.py -v

Registration is default-deny for images: only registries listed in the
ALLOWED_REGISTRIES environment variable are accepted. The autouse fixture below
sets it to registry.example.com for every test; individual tests change it to
exercise the policy. The policy itself is unit-tested without FastAPI in
test_image_policy.py and test_schema_rules.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from registration.app import _registry, app, get_image_scanner
from registration.image_check import ScanResult

DIGEST = "sha256:" + "a" * 64


@pytest.fixture(autouse=True)
def clean_registry():
    """Each test starts from an empty registry -- InMemoryConnectorRegistry
    is process-local, so tests would otherwise leak state into each other."""
    _registry._records.clear()
    yield


@pytest.fixture(autouse=True)
def allow_registry(monkeypatch):
    monkeypatch.setenv("ALLOWED_REGISTRIES", "registry.example.com")


@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_default_scanner():
    """Keep API tests independent of Docker and external registries."""
    class _PassingScanner:
        async def scan(self, image):
            return ScanResult(
                status="passed",
                detail="Mock scan passed",
            )

    app.dependency_overrides[get_image_scanner] = _PassingScanner
    yield
    app.dependency_overrides.pop(get_image_scanner, None)

VALID_PAYLOAD = {
    "name": "my_connector",
    "image": "registry.example.com/my-connector:1.0.0",
    "config_schema": {
        "type": "object",
        "properties": {"base_url": {"type": "string"}},
        "required": ["base_url"],
    },
    "credential_schema": {
        "type": "object",
        "properties": {"api_key": {"type": "string", "secret": True}},
        "required": ["api_key"],
    },
}


def post(client, **overrides):
    return client.post("/connectors/custom", json={**VALID_PAYLOAD, **overrides})


# ---- happy path ------------------------------------------------------------

def test_register_then_get_round_trip(client):
    reg = post(client)
    assert reg.status_code == 201
    assert reg.json()["name"] == "my_connector"
    assert reg.json()["image_check_status"] == "ok"

    got = client.get("/connectors/custom/my_connector")
    assert got.status_code == 200
    assert got.json()["image"] == VALID_PAYLOAD["image"]


def test_list_includes_registered_connectors(client):
    post(client)
    listed = client.get("/connectors/custom").json()
    assert [c["name"] for c in listed] == ["my_connector"]


def test_get_unknown_connector_is_404(client):
    res = client.get("/connectors/custom/does_not_exist")
    assert res.status_code == 404


def test_duplicate_name_is_409(client):
    post(client)
    assert post(client).status_code == 409


@pytest.mark.parametrize(
    "bad_name",
    ["My-Connector", "1connector", "connector name", "my-connector"],
)
def test_invalid_names_are_rejected(client, bad_name):
    assert post(client, name=bad_name).status_code == 422


# ---- schema validation -------------------------------------------------------

def test_flat_field_map_config_schema_is_rejected(client):
    """The exact bug we found in the TS connector guide: a flat
    {field: {required: true}} map instead of the {type, properties,
    required} envelope. This must be a 422, not a silently stored record."""
    res = post(client, config_schema={"base_url": {"type": "string", "required": True}})
    assert res.status_code == 422


def test_non_secret_credential_field_is_accepted(client):
    """Jira describes a plain `email` next to a secret `api_token`. The earlier
    rule ('every credential field must be secret') rejected this real connector."""
    creds = {
        "type": "object",
        "properties": {"email": {"type": "string"}, "api_token": {"type": "string", "secret": True}},
        "required": ["email", "api_token"],
    }
    assert post(client, credential_schema=creds).status_code == 201


def test_secret_field_in_config_schema_is_rejected(client):
    config = {
        "type": "object",
        "properties": {"base_url": {"type": "string"}, "token": {"type": "string", "secret": True}},
        "required": ["base_url"],
    }
    res = post(client, config_schema=config)
    assert res.status_code == 422
    assert "credential_schema" in res.text


@pytest.mark.parametrize("field", ["config_schema", "credential_schema"])
@pytest.mark.parametrize(
    "bad_schema",
    [
        {"type": "banana", "properties": {}, "required": []},
        {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["ghost"]},
        {"type": "object", "properties": {"a": "string"}, "required": []},
        {"type": "object", "properties": {"a": {}}, "required": []},
        {"type": "object", "properties": {"a": {"type": "strng"}}, "required": []},
        {"type": "object", "properties": {"a": {"type": "string", "secret": "yes"}}, "required": []},
        {"type": "object", "properties": {"bad name": {"type": "string"}}, "required": []},
    ],
)
def test_malformed_schema_contents_are_rejected(client, field, bad_schema):
    assert post(client, **{field: bad_schema}).status_code == 422


def test_oversized_schema_is_rejected(client):
    many = {"type": "object", "properties": {f"p{i}": {"type": "string"} for i in range(51)}, "required": []}
    assert post(client, config_schema=many).status_code == 422


def test_unknown_top_level_field_is_rejected(client):
    res = client.post("/connectors/custom", json={**VALID_PAYLOAD, "run_as_root": True})
    assert res.status_code == 422


# ---- image security: syntax, allowlist, pinning ---------------------------------

def test_implausible_image_reference_is_rejected(client):
    assert post(client, image="not an image reference").status_code == 422


@pytest.mark.parametrize(
    "image",
    [
        "http://169.254.169.254/latest/meta-data",   # cloud metadata endpoint
        "http://localhost:8080/evil",
        "file:///etc/passwd",
        "127.0.0.1:5000/evil:1",
        "10.0.0.5/internal/img:1",
        "localhost/evil:1",
        "user:pass@registry.example.com/x:1",        # credentials in the reference
        "registry.example.com/x:1;rm-rf-/",          # shell metacharacters
        "registry.example.com/$(whoami):1",
        "registry.example.com/../../etc/passwd:1",   # path traversal
        "registry.example.com/x:1\nHost: evil",
    ],
)
def test_hostile_image_references_are_rejected(client, image):
    assert post(client, image=image).status_code == 422
    assert client.get("/connectors/custom").json() == []   # nothing was stored


def test_registry_not_on_the_allowlist_is_rejected(client):
    res = post(client, image="evil.example.com/malware:1.0")
    assert res.status_code == 422
    assert "registry_not_allowed" in res.text
    assert client.get("/connectors/custom").json() == []


def test_nothing_is_allowed_when_no_registries_are_configured(client, monkeypatch):
    monkeypatch.delenv("ALLOWED_REGISTRIES", raising=False)
    res = post(client)
    assert res.status_code == 422
    assert "no_registries_configured" in res.text


def test_allowlist_can_hold_several_registries(client, monkeypatch):
    monkeypatch.setenv("ALLOWED_REGISTRIES", "registry.example.com, ghcr.io")
    assert post(client, image="ghcr.io/org/jira:2.0").status_code == 201


@pytest.mark.parametrize("image", ["registry.example.com/my-connector", "registry.example.com/my-connector:latest"])
def test_unpinned_images_are_rejected(client, image):
    res = post(client, image=image)
    assert res.status_code == 422
    assert "unpinned_image" in res.text


def test_digest_pinned_image_is_accepted(client):
    assert post(client, image=f"registry.example.com/my-connector@{DIGEST}").status_code == 201


# ---- scanning ------------------------------------------------------------------

def test_registration_is_rejected_when_scan_is_unavailable(
    client, scanner_returning
):
    scanner_returning("not_scanned", "Scanner is unavailable")

    res = post(client)

    assert res.status_code == 503
    assert client.get("/connectors/custom").json() == []

class _FixedScanner:
    def __init__(self, status, detail=""):
        self._result = ScanResult(status=status, detail=detail)

    async def scan(self, image):
        return self._result


@pytest.fixture
def scanner_returning():
    def install(status, detail=""):
        app.dependency_overrides[get_image_scanner] = lambda: _FixedScanner(status, detail)
    yield install
    app.dependency_overrides.pop(get_image_scanner, None)


def test_image_that_fails_the_scan_is_rejected(client, scanner_returning):
    scanner_returning("failed", "CVE-0000-0000 (critical)")
    res = post(client)
    assert res.status_code == 422
    assert "scan failed" in res.text
    assert client.get("/connectors/custom").json() == []


def test_image_that_passes_the_scan_is_recorded_as_passed(client, scanner_returning):
    scanner_returning("passed", "no findings")
    assert post(client).json()["scan_status"] == "passed"
