"""
Demo + test suite for POST /connectors/custom. Run this to see the whole
thing work end to end with zero real infrastructure:

    pytest tests/test_registration.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from registration.app import _registry, app


@pytest.fixture(autouse=True)
def clean_registry():
    """Each test starts from an empty registry -- InMemoryConnectorRegistry
    is process-local, so tests would otherwise leak state into each other."""
    _registry._records.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


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


def test_register_then_get_round_trip(client):
    reg = client.post("/connectors/custom", json=VALID_PAYLOAD)
    assert reg.status_code == 201
    assert reg.json()["name"] == "my_connector"
    assert reg.json()["image_check_status"] == "ok"

    got = client.get("/connectors/custom/my_connector")
    assert got.status_code == 200
    assert got.json()["image"] == VALID_PAYLOAD["image"]


def test_list_includes_registered_connectors(client):
    client.post("/connectors/custom", json=VALID_PAYLOAD)
    listed = client.get("/connectors/custom").json()
    assert [c["name"] for c in listed] == ["my_connector"]


def test_get_unknown_connector_is_404(client):
    res = client.get("/connectors/custom/does_not_exist")
    assert res.status_code == 404


def test_duplicate_name_is_409(client):
    client.post("/connectors/custom", json=VALID_PAYLOAD)
    dup = client.post("/connectors/custom", json=VALID_PAYLOAD)
    assert dup.status_code == 409


@pytest.mark.parametrize(
    "bad_name",
    ["My-Connector", "1connector", "connector name", "my-connector"],
)
def test_invalid_names_are_rejected(client, bad_name):
    payload = {**VALID_PAYLOAD, "name": bad_name}
    assert client.post("/connectors/custom", json=payload).status_code == 422


def test_flat_field_map_config_schema_is_rejected(client):
    """The exact bug we found in the TS connector guide: a flat
    {field: {required: true}} map instead of the {type, properties,
    required} envelope. This must be a 422, not a silently stored record."""
    payload = {
        **VALID_PAYLOAD,
        "config_schema": {"base_url": {"type": "string", "required": True}},
    }
    assert client.post("/connectors/custom", json=payload).status_code == 422


def test_credential_field_not_marked_secret_is_rejected(client):
    payload = {
        **VALID_PAYLOAD,
        "credential_schema": {
            "type": "object",
            "properties": {"api_key": {"type": "string"}},  # missing "secret": true
            "required": ["api_key"],
        },
    }
    assert client.post("/connectors/custom", json=payload).status_code == 422


def test_implausible_image_reference_is_rejected(client):
    payload = {**VALID_PAYLOAD, "image": "not an image reference"}
    assert client.post("/connectors/custom", json=payload).status_code == 422
