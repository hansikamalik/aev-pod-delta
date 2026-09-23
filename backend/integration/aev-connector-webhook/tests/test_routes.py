import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aev_connectors.webhook import routes
from aev_connectors.webhook.auth import build_auth_headers
from aev_connectors.webhook.config import RetryPolicy, WebhookConfig
from aev_connectors.webhook.connector import WebhookConnector

SECRET = "whsec_test_123"


class FakePlatform:
    def __init__(self) -> None:
        self.assets: list = []
        self.findings: list = []

    async def upsert_assets(self, org_id, assets):
        self.assets.extend(assets)

    async def upsert_findings(self, org_id, findings):
        self.findings.extend(findings)


@pytest.fixture
def config() -> WebhookConfig:
    return WebhookConfig(
        org_id="org_1",
        connector_id="webhook-custom-1",
        target_url="https://example.test/hook",
        signing_secret=SECRET,
        retry=RetryPolicy(max_attempts=2, base_delay_seconds=0.01, jitter=False),
    )


@pytest.fixture
def client(config) -> TestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = WebhookConnector(config, platform_client=FakePlatform(), http_client=http)
    routes.configure(connector)

    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def test_health(client):
    response = client.get("/connectors/webhook/health")
    assert response.status_code == 200
    assert response.json()["connector"] == "webhook"


def test_inbound_event_accepted(client, config):
    payload = {
        "event_type": "asset.created",
        "assets": [{"id": "i-1", "hostname": "web-01", "type": "vm"}],
    }
    body = json.dumps(payload).encode()
    response = client.post(
        "/connectors/webhook/events",
        content=body,
        headers=build_auth_headers(config, body),
    )
    assert response.status_code == 202
    assert response.json()["records_buffered"] == 1


def test_inbound_event_unsigned_rejected(client):
    response = client.post("/connectors/webhook/events", json={"event_type": "asset.created"})
    assert response.status_code == 401


def test_inbound_invalid_json_rejected(client, config):
    body = b"not json"
    response = client.post(
        "/connectors/webhook/events",
        content=body,
        headers=build_auth_headers(config, body),
    )
    assert response.status_code == 400


def test_sync_drains_buffer(client, config):
    payload = {"event_type": "asset.created", "assets": [{"id": "i-1", "type": "vm"}]}
    body = json.dumps(payload).encode()
    client.post("/connectors/webhook/events", content=body, headers=build_auth_headers(config, body))

    response = client.post("/connectors/webhook/sync")
    assert response.status_code == 200
    assert response.json()["assets_pushed"] == 1


def test_subscription_crud(client):
    created = client.post(
        "/connectors/webhook/subscriptions",
        json={"target_url": "https://a.test/hook", "event_types": ["asset.created"]},
    )
    assert created.status_code == 201
    sub_id = created.json()["id"]

    assert len(client.get("/connectors/webhook/subscriptions").json()) == 1

    patched = client.patch(f"/connectors/webhook/subscriptions/{sub_id}", json={"active": False})
    assert patched.json()["active"] is False

    assert client.delete(f"/connectors/webhook/subscriptions/{sub_id}").status_code == 204
    assert client.get("/connectors/webhook/subscriptions").json() == []


def test_unsupported_event_type_rejected(client):
    response = client.post(
        "/connectors/webhook/subscriptions",
        json={"target_url": "https://a.test/hook", "event_types": ["asset.exploded"]},
    )
    assert response.status_code == 422


def test_emit_and_delivery_log(client):
    client.post(
        "/connectors/webhook/subscriptions",
        json={"target_url": "https://a.test/hook", "event_types": ["asset.created"]},
    )
    emitted = client.post(
        "/connectors/webhook/emit",
        json={"event_type": "asset.created", "payload": {"id": "i-1"}},
    )
    assert emitted.status_code == 200
    assert emitted.json()[0]["status"] == "delivered"

    deliveries = client.get("/connectors/webhook/deliveries")
    assert len(deliveries.json()) == 1


def test_redeliver_unknown_id_is_404(client):
    assert client.post("/connectors/webhook/deliveries/dlv_nope/redeliver").status_code == 404
