import time

import pytest

from aev_connectors.webhook.auth import AuthError, build_auth_headers, verify_inbound
from aev_connectors.webhook.config import WebhookConfig
from aev_connectors.webhook.signing import (
    SIGNATURE_HEADER,
    SignatureError,
    build_signature_header,
    compute_signature,
    verify_signature,
)

SECRET = "whsec_test_123"
BODY = b'{"id":"evt_1","type":"asset.created"}'


def test_signature_is_deterministic_for_same_timestamp():
    assert compute_signature(SECRET, BODY, 1_726_550_400) == compute_signature(
        SECRET, BODY, 1_726_550_400
    )


def test_signature_changes_with_body():
    a = compute_signature(SECRET, BODY, 1_726_550_400)
    b = compute_signature(SECRET, BODY + b" ", 1_726_550_400)
    assert a != b


def test_round_trip_verifies():
    header, ts = build_signature_header(SECRET, BODY)
    verify_signature(SECRET, BODY, header, now=ts)


def test_tampered_body_rejected():
    header, ts = build_signature_header(SECRET, BODY)
    with pytest.raises(SignatureError, match="mismatch"):
        verify_signature(SECRET, b'{"id":"evt_1","type":"asset.deleted"}', header, now=ts)


def test_stale_timestamp_rejected():
    header, ts = build_signature_header(SECRET, BODY)
    with pytest.raises(SignatureError, match="tolerance"):
        verify_signature(SECRET, BODY, header, tolerance_seconds=300, now=ts + 301)


def test_future_timestamp_rejected():
    header, ts = build_signature_header(SECRET, BODY)
    with pytest.raises(SignatureError, match="tolerance"):
        verify_signature(SECRET, BODY, header, tolerance_seconds=300, now=ts - 301)


def test_missing_header_rejected():
    with pytest.raises(SignatureError, match="missing"):
        verify_signature(SECRET, BODY, None)


@pytest.mark.parametrize("header", ["", "v1=abc", "t=notanumber,v1=abc", "t=123"])
def test_malformed_header_rejected(header):
    with pytest.raises(SignatureError):
        verify_signature(SECRET, BODY, header)


def test_secret_rotation_accepts_old_secret():
    header, ts = build_signature_header("old_secret", BODY)
    verify_signature("new_secret,old_secret", BODY, header, now=ts)


def _config(**overrides) -> WebhookConfig:
    base = dict(
        org_id="org_1",
        connector_id="webhook-custom-1",
        target_url="https://example.test/hook",
        signing_secret=SECRET,
    )
    base.update(overrides)
    return WebhookConfig(**base)


def test_bearer_headers_round_trip():
    config = _config(auth_mode="bearer", auth_token="tok_abc")
    headers = build_auth_headers(config, BODY)
    assert headers["Authorization"] == "Bearer tok_abc"
    verify_inbound(config, BODY, headers)


def test_basic_headers_round_trip():
    config = _config(auth_mode="basic", basic_username="u", basic_password="p")
    headers = build_auth_headers(config, BODY)
    assert headers["Authorization"].startswith("Basic ")
    verify_inbound(config, BODY, headers)


def test_wrong_bearer_token_rejected():
    config = _config(auth_mode="bearer", auth_token="tok_abc")
    headers = build_auth_headers(config, BODY)
    headers["Authorization"] = "Bearer wrong"
    with pytest.raises(AuthError, match="bearer"):
        verify_inbound(config, BODY, headers)


def test_header_lookup_is_case_insensitive():
    config = _config()
    headers = build_auth_headers(config, BODY)
    lowered = {k.lower(): v for k, v in headers.items()}
    verify_inbound(config, BODY, lowered)


def test_auth_mode_none_skips_signature():
    config = _config(auth_mode="none")
    verify_inbound(config, BODY, {})


def test_hmac_mode_requires_signature():
    config = _config()
    with pytest.raises(AuthError, match="missing"):
        verify_inbound(config, BODY, {})


def test_signature_header_name_is_stable():
    config = _config()
    headers = build_auth_headers(config, BODY)
    assert SIGNATURE_HEADER in headers
    assert int(headers["X-AEV-Timestamp"]) == pytest.approx(int(time.time()), abs=5)
