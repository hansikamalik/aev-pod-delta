import json

import httpx
import pytest

from aev_connectors.webhook.auth import AuthError, build_auth_headers
from aev_connectors.webhook.client import DeliveryClient
from aev_connectors.webhook.config import RetryPolicy, WebhookConfig
from aev_connectors.webhook.connector import WebhookConnector
from aev_connectors.webhook.delivery_log import InMemoryDeliveryLog
from aev_connectors.webhook.models import DeliveryStatus, Event, Subscription
from aev_connectors.webhook.normalizer import NormalizationError, normalize_asset, normalize_finding

SECRET = "whsec_test_123"


@pytest.fixture
def config() -> WebhookConfig:
    return WebhookConfig(
        org_id="org_1",
        connector_id="webhook-custom-1",
        target_url="https://example.test/hook",
        signing_secret=SECRET,
        retry=RetryPolicy(max_attempts=3, base_delay_seconds=0.01, jitter=False),
    )


@pytest.fixture
def subscription() -> Subscription:
    return Subscription(
        org_id="org_1",
        connector_id="webhook-custom-1",
        target_url="https://example.test/hook",
        event_types=["asset.created"],
    )


class FakePlatform:
    def __init__(self) -> None:
        self.assets: list = []
        self.findings: list = []

    async def upsert_assets(self, org_id, assets):
        self.assets.extend(assets)

    async def upsert_findings(self, org_id, findings):
        self.findings.extend(findings)


async def _noop_sleep(_seconds: float) -> None:
    return None


# ------------------------------------------------------------------ normalize

def test_normalize_asset_resolves_aliases():
    asset = normalize_asset({"id": "i-123", "hostname": "web-01", "type": "EC2", "ip": "10.0.0.4"})
    assert asset.external_id == "i-123"
    assert asset.name == "web-01"
    assert asset.asset_type == "ec2"
    assert asset.ip_addresses == ["10.0.0.4"]


def test_normalize_asset_without_identifier_raises():
    with pytest.raises(NormalizationError, match="identifier"):
        normalize_asset({"hostname": "web-01"})


@pytest.mark.parametrize(
    "raw,expected",
    [("CRITICAL", "critical"), ("P2", "high"), ("moderate", "medium"), ("weird", "info"), (None, "info")],
)
def test_severity_aliases(raw, expected):
    finding = normalize_finding({"id": "f1", "asset_id": "i-123", "severity": raw})
    assert finding.severity == expected


def test_normalize_finding_requires_asset_link():
    with pytest.raises(NormalizationError, match="asset"):
        normalize_finding({"id": "f1"})


# ------------------------------------------------------------------ connector

@pytest.mark.asyncio
async def test_authenticate(config):
    assert await WebhookConnector(config).authenticate() is True


@pytest.mark.asyncio
async def test_inbound_to_push_round_trip(config):
    platform = FakePlatform()
    connector = WebhookConnector(config, platform_client=platform)

    payload = {
        "event_type": "asset.created",
        "assets": [{"id": "i-1", "hostname": "web-01", "type": "vm"}],
        "findings": [{"id": "f-1", "asset_id": "i-1", "severity": "high", "title": "Open port"}],
    }
    body = json.dumps(payload).encode()
    headers = build_auth_headers(config, body)

    assert connector.accept_inbound(body, headers, payload) == 2
    assert len(await connector.discover()) == 1

    result = await connector.ingest()
    assert result.ok
    assert result.assets_pushed == 1
    assert result.findings_pushed == 1
    assert len(platform.assets) == 1

    # Buffer is drained, so a second sync is a no-op.
    second = await connector.ingest()
    assert second.assets_discovered == 0


@pytest.mark.asyncio
async def test_inbound_rejects_bad_signature(config):
    connector = WebhookConnector(config)
    payload = {"event_type": "asset.created", "assets": []}
    body = json.dumps(payload).encode()
    headers = build_auth_headers(config, body)
    headers["X-AEV-Signature"] = "t=1,v1=deadbeef"
    with pytest.raises(AuthError):
        connector.accept_inbound(body, headers, payload)


@pytest.mark.asyncio
async def test_push_without_platform_client_records_error(config):
    result = await WebhookConnector(config).push([], [])
    assert not result.ok


# ------------------------------------------------------------------- delivery

@pytest.mark.asyncio
async def test_successful_delivery_signs_request(config, subscription):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["body"] = request.content
        return httpx.Response(200)

    log = InMemoryDeliveryLog()
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = DeliveryClient(config, log, http, sleep=_noop_sleep)
        record = await client.deliver(Event(org_id="org_1", event_type="asset.created"), subscription)

    assert record.status == DeliveryStatus.DELIVERED
    assert record.attempt_count == 1
    assert "x-aev-signature" in seen["headers"]
    assert seen["headers"]["x-aev-attempt"] == "1"


@pytest.mark.asyncio
async def test_retries_then_succeeds(config, subscription):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503 if calls["n"] < 3 else 200)

    log = InMemoryDeliveryLog()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = DeliveryClient(config, log, http, sleep=_noop_sleep)
        record = await client.deliver(Event(org_id="org_1", event_type="asset.created"), subscription)

    assert calls["n"] == 3
    assert record.status == DeliveryStatus.DELIVERED
    assert record.attempt_count == 3


@pytest.mark.asyncio
async def test_permanent_failure_stops_immediately(config, subscription):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401)

    log = InMemoryDeliveryLog()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = DeliveryClient(config, log, http, sleep=_noop_sleep)
        record = await client.deliver(Event(org_id="org_1", event_type="asset.created"), subscription)

    assert calls["n"] == 1
    assert record.status == DeliveryStatus.FAILED


@pytest.mark.asyncio
async def test_exhausted_retries_are_dead_lettered(config, subscription):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    log = InMemoryDeliveryLog()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = DeliveryClient(config, log, http, sleep=_noop_sleep)
        record = await client.deliver(Event(org_id="org_1", event_type="asset.created"), subscription)

    assert record.attempt_count == config.retry.max_attempts
    assert record.status == DeliveryStatus.DEAD_LETTERED
    assert log.stats("org_1")["dead_lettered"] == 1


@pytest.mark.asyncio
async def test_transport_error_is_retried(config, subscription):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ConnectTimeout("boom")

    log = InMemoryDeliveryLog()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = DeliveryClient(config, log, http, sleep=_noop_sleep)
        record = await client.deliver(Event(org_id="org_1", event_type="asset.created"), subscription)

    assert calls["n"] == config.retry.max_attempts
    assert record.attempts[-1].error is not None


@pytest.mark.asyncio
async def test_emit_fans_out_to_matching_subscriptions_only(config):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        connector = WebhookConnector(config, http_client=http)
        connector.subscribe("https://a.test/hook", ["asset.created"])
        connector.subscribe("https://b.test/hook", ["exposure.created"])
        records = await connector.emit(Event(org_id="org_1", event_type="asset.created"))

    assert len(records) == 1
    assert records[0].target_url == "https://a.test/hook"


@pytest.mark.asyncio
async def test_health_check_reports_stats(config):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        connector = WebhookConnector(config, http_client=http)
        connector.subscribe("https://a.test/hook", ["asset.created"])
        health = await connector.health_check()

    assert health["healthy"] is True
    assert health["subscriptions"] == 1
    assert health["connector"] == "webhook"
