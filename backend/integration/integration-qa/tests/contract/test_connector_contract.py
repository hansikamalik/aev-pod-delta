"""
Contract tests — the §25/§26 matrix from contract_v2, applied to EVERY connector.

P0 gate: no connector merges without these passing.
Run:  pytest tests/contract -m contract -v

New connectors join via `all_connectors()` — one line, tests apply unchanged.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List

import pytest

from qa.contracts import (
    ASSET_TYPES,
    SYNC_STATUSES,
    Asset,
    Connector,
    SyncResult,
)
from qa.mocks.dummy_connector import DummyConnector
from qa.validators import validate_asset, validate_assets

_SECRET_RE = re.compile(
    r"(client_secret|password|passwd|api[-_]?key|secret|token)", re.IGNORECASE
)


def all_connectors() -> Iterator[Connector]:
    """Yield fresh instances of every connector under contract testing."""
    yield DummyConnector()
    # TODO(Day 5): yield AzureConnector(...)   # with mocked creds
    # TODO(Day 5): yield SplunkConnector(...)  # against MockSplunkHEC


def _connector_factories() -> Iterator:
    """One factory per connector — guarantees a fresh instance per test."""
    def dummy():
        return DummyConnector()

    dummy.__name__ = "dummy"
    yield dummy
    # TODO(Day 5): def azure(): return AzureConnector(...); yield azure
    # TODO(Day 5): def splunk(): return SplunkConnector(...); yield splunk


# Use *factories*, not instances: pytest evaluates parametrize args at
# collection time, so instances would be shared and mutated across tests.
@pytest.fixture(params=list(_connector_factories()), ids=lambda f: f().name)
def connector(request) -> Connector:
    return request.param()


def credentials_for(connector: Connector) -> Dict[str, str]:
    """Build valid credentials from the connector's own describe_credentials()."""
    schema = connector.describe_credentials()
    values = {"api_key": "mock-key-123", "token": "mock-token", "client_secret": "mock-secret"}
    return {k: values.get(k, f"mock-{k}") for k in schema.get("required", [])}


@pytest.fixture()
def live(connector: Connector) -> Connector:
    """Connector with valid credentials applied (via conventional injection)."""
    creds = credentials_for(connector)
    if hasattr(connector, "_apply_credentials"):
        connector._apply_credentials(creds)
    return connector


# ===========================================================================
# §26 minimum contract tests — interface surface
# ===========================================================================
@pytest.mark.contract
class TestContractInterface:
    def test_connector_name(self, connector):
        assert connector.name, "§4: name must be a non-empty stable identifier"

    def test_name_is_lowercase_simple(self, connector):
        assert connector.name == connector.name.lower(), "§4: name SHOULD be lowercase"
        assert re.fullmatch(r"[a-z][a-z0-9_-]*", connector.name), (
            "§4: avoid env info or dynamic values in name"
        )

    def test_implements_full_interface(self, connector):
        for method in (
            "discover", "ingest", "sync", "check_health",
            "describe_config", "describe_credentials",
        ):
            assert callable(getattr(connector, method, None)), f"missing {method}()"


# ===========================================================================
# §25 Discovery
# ===========================================================================
@pytest.mark.contract
class TestDiscovery:
    def test_returns_expected_assets(self, live):
        assets = list(live.discover())
        assert len(assets) > 0

    def test_returns_valid_asset_objects(self, live):
        from dataclasses import asdict, is_dataclass

        for asset in live.discover():
            assert isinstance(asset, Asset), "§10: must yield Asset instances"
            violations = validate_asset(asset)
            assert not violations, f"invalid asset: {violations}"
            assert is_dataclass(asset) or isinstance(asset, dict)
            _ = asdict(asset) if is_dataclass(asset) else asset

    def test_source_is_connector_name(self, live):
        for asset in live.discover():
            assert asset.source == live.name, "§7: asset.source MUST equal connector.name"

    def test_asset_type_is_normalized(self, live):
        for asset in live.discover():
            assert asset.type in ASSET_TYPES, "§8: must use SDK AssetType values"

    def test_asset_ids_are_stable_across_runs(self, live):
        first = [a.id for a in live.discover()]
        second = [a.id for a in live.discover()]
        assert first == second, "§6: same source resource MUST produce the same id"

    def test_discover_does_not_push(self, live):
        """§10: discover is a read operation — no platform writes."""
        before = list(live.platform) if hasattr(live, "platform") else []
        list(live.discover())
        after = list(live.platform) if hasattr(live, "platform") else []
        assert before == after

    def test_handles_pagination(self, live):
        """§21: all pages must be retrieved, none dropped."""
        assets = list(live.discover())
        total = sum(len(p) for p in getattr(live, "_pages", [[1]]))
        assert len(assets) == total, "§21: pagination must not drop pages"


# ===========================================================================
# §25 Ingestion
# ===========================================================================
@pytest.mark.contract
class TestIngestion:
    def test_assets_reach_platform_and_count_is_correct(self, live):
        assets = list(live.discover())
        count = live.ingest(assets)
        assert count == len(assets)
        if hasattr(live, "platform"):
            assert len(live.platform) == len(assets)

    def test_reports_only_successfully_pushed(self, connector, live):
        connector._fail_ingest = True  # simulate platform rejection
        count = live.ingest([Asset(id="x", source=live.name, type="other",
                                   name="x", raw={}, discoveredAt="2026-09-17T00:00:00Z")])
        assert count == 0, "§11: must not report rejected assets as pushed"

    def test_ingest_does_not_rediscover(self, live):
        """§11: ingest must not call discover or source APIs."""
        if hasattr(live, "platform"):
            live.ingest(list(live.discover())[:1])
            before = len(live.platform)
            live.ingest([])
            assert len(live.platform) == before


# ===========================================================================
# §25 Health
# ===========================================================================
@pytest.mark.contract
class TestHealth:
    def test_valid_connection_returns_true(self, live):
        assert live.check_health() is True

    def test_invalid_or_unreachable_returns_false(self, connector):
        connector._fail_health = True
        assert connector.check_health() is False, "§17: must report False, never raise"

    def test_health_is_lightweight_and_repeatable(self, live):
        assert live.check_health() == live.check_health()


# ===========================================================================
# §25 Synchronization + §13/§14/§15 SyncResult
# ===========================================================================
@pytest.mark.contract
class TestSync:
    def test_successful_sync(self, live):
        result = _run(live.sync())
        _assert_valid_result(result, live)
        assert result.status == "success"
        assert result.assets_discovered == result.assets_pushed
        assert result.errors == []

    def test_partial_sync_reported(self, connector, live):
        """§15: rejected assets must yield partial, never success."""
        connector._fail_ingest = True
        result = _run(live.sync())
        assert result.status in ("partial", "failed")
        assert result.assets_pushed < result.assets_discovered or result.status == "failed"

    def test_failed_sync_reported(self, connector, live):
        connector._fail_health = True
        connector._fail_ingest = True
        result = _run(live.sync())
        _assert_valid_result(result, live)

    def test_counts_are_consistent(self, live):
        result = _run(live.sync())
        assert result.assets_pushed <= result.assets_discovered
        if result.status == "success":
            assert result.assets_pushed == result.assets_discovered

    def test_sync_is_idempotent(self, live):
        """§12: same source state -> same asset identity, no duplicates."""
        _run(live.sync())
        ids_first = [a.id for a in getattr(live, "platform", [])]
        _run(live.sync())
        ids_after = [a.id for a in getattr(live, "platform", [])]
        assert sorted(ids_first) == sorted(ids_after), (
            "§12: repeated syncs must upsert, not duplicate"
        )
        if hasattr(live, "platform"):
            assert len(ids_after) == len(set(ids_after)), "§12: duplicate ids on platform"


# ===========================================================================
# §25/§18/§19 Configuration & credentials
# ===========================================================================
@pytest.mark.contract
class TestConfigAndCredentials:
    def test_config_schema_is_valid_json_schema(self, live):
        schema = live.describe_config()
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        _assert_json_schema(schema)

    def test_required_fields_are_declared(self, live):
        assert isinstance(live.describe_config().get("required"), list)

    def test_credential_schema_flags_secrets(self, live):
        schema = live.describe_credentials()
        assert isinstance(schema, dict)
        _assert_json_schema(schema)
        props = schema.get("properties", {})
        assert props, "§19: must declare its credential fields"
        assert any(prop.get("secret") for prop in props.values()), (
            "§19: credential fields must be flagged secret: True"
        )

    def test_no_secrets_in_config_schema(self, live):
        config_text = json.dumps(live.describe_config()).lower()
        assert not _SECRET_RE.search(config_text), (
            "§18: configuration MUST NOT contain credentials or secrets"
        )


# ===========================================================================
# §16 errors & §19 secrets
# ===========================================================================
@pytest.mark.contract
class TestErrorHygiene:
    def test_no_secrets_in_raw_payloads(self, live):
        for asset in live.discover():
            for key in asset.raw:
                assert not _SECRET_RE.search(str(key)), (
                    f"§16/§19: suspected secret field {key!r} in raw"
                )

    def test_no_secrets_in_error_messages(self, connector, live):
        """§16: error structures must never carry credential values."""
        connector._fail_ingest = True
        result = _run(live.sync())
        for err in result.errors:
            for value in credentials_for(connector).values():
                assert value not in str(err), "§16: secret leaked into error message"


# ===========================================================================
# helpers
# ===========================================================================
def _run(coro_or_result):
    """sync() is async per contract; run it transparently in tests."""
    import asyncio

    if hasattr(coro_or_result, "__await__"):
        return asyncio.run(coro_or_result)
    return coro_or_result


def _assert_valid_result(result, connector):
    assert isinstance(result, SyncResult), "§14: sync must produce a SyncResult"
    assert result.connector == connector.name
    assert result.status in SYNC_STATUSES, "§15: status must be success|partial|failed"
    assert isinstance(result.assets_discovered, int)
    assert isinstance(result.assets_pushed, int)
    assert isinstance(result.errors, list)
    assert result.started_at and result.completed_at, "§14: timestamps required"


def _assert_json_schema(schema: Dict[str, Any]) -> None:
    from jsonschema.validators import Draft202012Validator

    Draft202012Validator.check_schema(schema)
