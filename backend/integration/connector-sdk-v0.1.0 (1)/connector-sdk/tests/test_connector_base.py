"""Tests for the Connector base class and default sync() (Sections 3-4, 13-16)."""

import pytest

from connector_sdk import (
    Asset,
    AssetType,
    Connector,
    ContractViolation,
    SyncStatus,
)
from connector_sdk.testing import FakeConnector, InMemoryPlatformClient, run_sync


class TestNameValidation:
    def test_missing_name_is_rejected(self):
        class Nameless(FakeConnector):
            name = ""

        with pytest.raises(ContractViolation, match="name"):
            Nameless()

    @pytest.mark.parametrize("bad", ["Azure", "aws-production", "aws 1", "1aws", "aws-123"])
    def test_malformed_names_rejected(self, bad):
        class Bad(FakeConnector):
            name = bad

        with pytest.raises(ContractViolation):
            Bad()


class TestAbstractInterface:
    def test_cannot_instantiate_base_class(self):
        with pytest.raises(TypeError):
            Connector()  # type: ignore[abstract]

    def test_partial_implementation_is_rejected(self):
        class Incomplete(Connector):
            name = "incomplete"

            def discover(self):
                return []

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


class TestDiscoverValidated:
    def test_rejects_non_asset(self):
        class BadYield(FakeConnector):
            def discover(self):
                yield {"id": "not-an-asset"}

        with pytest.raises(ContractViolation, match="expected Asset"):
            list(BadYield().discover_validated())

    def test_rejects_mismatched_source(self):
        class WrongSource(FakeConnector):
            def discover(self):
                yield Asset(
                    id="x", source="someone_else", type=AssetType.OTHER, name="x", raw={}
                )

        with pytest.raises(ContractViolation, match="does not match connector name"):
            list(WrongSource().discover_validated())

    def test_rejects_duplicate_ids(self):
        class Dupes(FakeConnector):
            def discover(self):
                for _ in range(2):
                    yield Asset(
                        id="same", source=self.name, type=AssetType.OTHER, name="x", raw={}
                    )

        with pytest.raises(ContractViolation, match="Duplicate asset id"):
            list(Dupes().discover_validated())


class TestDefaultSync:
    def test_successful_sync(self):
        connector = FakeConnector()
        result = run_sync(connector)
        assert result.status is SyncStatus.SUCCESS
        assert result.assets_discovered == 3
        assert result.assets_pushed == 3
        assert result.errors == []
        assert result.connector == "fake"

    def test_timestamps_are_recorded(self):
        result = run_sync(FakeConnector())
        assert result.completed_at is not None
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0

    def test_partial_sync_when_platform_rejects(self):
        platform = InMemoryPlatformClient(reject_ids={"vm-0002"})
        result = run_sync(FakeConnector(platform=platform))
        assert result.status is SyncStatus.PARTIAL
        assert result.assets_discovered == 3
        assert result.assets_pushed == 2
        assert len(result.errors) == 1

    def test_failed_sync_on_source_outage(self):
        result = run_sync(FakeConnector(raise_on_discover=True))
        assert result.status is SyncStatus.FAILED
        assert result.assets_discovered == 0
        assert result.errors
        assert result.errors[0]["error_type"] == "SourceUnavailableError"
        assert result.errors[0]["retryable"] is True

    def test_failed_sync_when_platform_unavailable(self):
        platform = InMemoryPlatformClient(fail_entirely=True)
        result = run_sync(FakeConnector(platform=platform))
        assert result.status is SyncStatus.FAILED

    def test_empty_discovery_is_not_a_failure(self):
        result = run_sync(FakeConnector(resources=[]))
        assert result.status is SyncStatus.SUCCESS
        assert result.assets_discovered == 0

    def test_sync_never_raises_on_unexpected_error(self):
        class Exploding(FakeConnector):
            def discover(self):
                raise RuntimeError("boom")

        result = run_sync(Exploding())
        assert result.status is SyncStatus.FAILED
        assert "RuntimeError" in result.errors[0]["message"]

    @pytest.mark.parametrize("bad_return", ["3", None, 3.0, True])
    def test_ingest_must_return_int(self, bad_return):
        class BadIngest(FakeConnector):
            def ingest(self, assets):
                return bad_return

        result = run_sync(BadIngest())
        assert result.status is SyncStatus.FAILED

    def test_ingest_cannot_overreport(self):
        class Liar(FakeConnector):
            def ingest(self, assets):
                return len(list(assets)) + 10

        result = run_sync(Liar())
        assert result.status is SyncStatus.FAILED

    def test_sync_blocking_matches_async(self):
        result = FakeConnector().sync_blocking()
        assert result.status is SyncStatus.SUCCESS


class TestIdempotency:
    def test_repeated_sync_does_not_duplicate_assets(self):
        platform = InMemoryPlatformClient()
        connector = FakeConnector(platform=platform)
        for _ in range(3):
            connector.sync_blocking()
        # Upsert semantics: three runs, still three assets.
        assert platform.count == 3
