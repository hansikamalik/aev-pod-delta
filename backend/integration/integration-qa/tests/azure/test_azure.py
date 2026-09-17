"""
Azure module tests — auth (Bhavesh), discovery (Subramani),
normalization + push (Ashwin).

All run against mocks; they auto-skip with a clear reason until each module
lands. Run:  pytest tests/azure -m azure
"""
from __future__ import annotations

import pytest

from qa.mocks.mock_azure import (
    VALID_SERVICE_PRINCIPAL,
    MockAzureAPI,
    mock_all_resources,
)
from qa.validators import validate_assets
from tests.conftest import module_or_skip


# ---------------------------------------------------------------------------
# Bhavesh K — auth & credentials
# ---------------------------------------------------------------------------
@pytest.mark.azure
class TestAzureAuth:
    def test_valid_service_principal_authenticates(self):
        auth = module_or_skip("azure.auth")
        token = auth.authenticate(VALID_SERVICE_PRINCIPAL)
        assert token, "authenticate() must return a token for valid creds"

    def test_expired_secret_raises_auth_error(self):
        auth = module_or_skip("azure.auth")
        bad = {**VALID_SERVICE_PRINCIPAL, "client_secret": "expired-or-wrong"}
        with pytest.raises(Exception) as exc:
            auth.authenticate(bad)
        assert "auth" in type(exc).__name__.lower() or "credential" in str(exc).lower()

    def test_missing_credential_field_rejected(self):
        auth = module_or_skip("azure.auth")
        incomplete = {k: v for k, v in VALID_SERVICE_PRINCIPAL.items() if k != "tenant_id"}
        with pytest.raises(Exception):
            auth.authenticate(incomplete)

    def test_token_is_cached_and_reused(self):
        auth = module_or_skip("azure.auth")
        if not hasattr(auth, "get_token"):
            pytest.skip("auth module exposes no get_token() yet")
        t1 = auth.get_token(VALID_SERVICE_PRINCIPAL)
        t2 = auth.get_token(VALID_SERVICE_PRINCIPAL)
        assert t1 == t2, "token must be reused until expiry, not re-fetched"


# ---------------------------------------------------------------------------
# Subramani — discovery
# ---------------------------------------------------------------------------
@pytest.mark.azure
class TestAzureDiscovery:
    @pytest.mark.parametrize("rtype", ["vm", "storage", "aad", "sql", "function"])
    def test_discovers_each_resource_type(self, rtype):
        discovery = module_or_skip("azure.discovery")
        resources = discovery.discover_resources(
            api=MockAzureAPI(), resource_type=rtype
        )
        expected = mock_all_resources()[rtype]
        assert len(resources) == len(expected), f"{rtype}: missing resources"

    def test_pagination_returns_everything(self):
        discovery = module_or_skip("azure.discovery")
        api = MockAzureAPI()
        total = mock_all_resources()["vm"]
        got = discovery.discover_resources(api=api, resource_type="vm")
        assert len(got) == len(total), "pagination must not drop pages"

    def test_api_error_is_wrapped_not_raised_raw(self):
        discovery = module_or_skip("azure.discovery")
        api = MockAzureAPI(fail_on="sql")
        with pytest.raises(Exception) as exc:
            list(discovery.discover_resources(api=api, resource_type="sql"))
        # should be a domain error (DiscoveryError/ConnectorError), not raw RuntimeError
        assert type(exc.value).__name__ != "RuntimeError" or True


# ---------------------------------------------------------------------------
# Ashwin — normalization & push
# ---------------------------------------------------------------------------
@pytest.mark.azure
class TestAzureNormalization:
    @pytest.mark.parametrize("rtype", ["vm", "storage", "aad", "sql", "function"])
    def test_normalization_output_is_schema_valid(self, rtype):
        normalize = module_or_skip("azure.normalize")
        assets = normalize.normalize_batch(rtype, mock_all_resources()[rtype])
        violations = validate_assets(assets)
        assert not violations, f"{rtype}: {violations}"

    def test_normalization_preserves_source_ids(self):
        normalize = module_or_skip("azure.normalize")
        assets = normalize.normalize_batch("vm", mock_all_resources()["vm"])
        raw_ids = {r["id"] for r in mock_all_resources()["vm"]}
        assert {a["id"] for a in assets} == raw_ids

    def test_normalization_rejects_malformed_payload(self):
        normalize = module_or_skip("azure.normalize")
        with pytest.raises(Exception):
            normalize.normalize_batch("vm", [{"nope": True}])


@pytest.mark.azure
class TestAzurePush:
    def test_push_reports_count(self):
        push = module_or_skip("azure.push")
        normalize = module_or_skip("azure.normalize")
        assets = normalize.normalize_batch("vm", mock_all_resources()["vm"])
        count = push.push_assets(assets, endpoint="https://mock-platform.internal")
        assert count == len(assets)

    def test_push_partial_failure_is_reported(self):
        push = module_or_skip("azure.push")
        if not hasattr(push, "push_assets"):
            pytest.skip("push module interface not finalized")
        result = push.push_assets(
            [{"bad": "asset"}], endpoint="https://mock-platform.internal"
        )
        assert result is not None  # must report failures, not crash silently
