"""Tests for Entra ID push (wrapper around shared PlatformClient)."""
from unittest.mock import MagicMock

from connectors.microsoft_entra_id.push import push_to_platform


def test_push_to_platform_delegates_to_client():
    client = MagicMock()
    client.push.return_value = {"assets": 2, "findings": 1}

    result = push_to_platform(assets=["a1", "a2"], findings=["f1"], client=client)

    client.push.assert_called_once_with(["a1", "a2"], ["f1"])
    assert result == {"assets": 2, "findings": 1}


def test_push_to_platform_creates_default_client_when_none_given(monkeypatch):
    created = MagicMock()
    created.push.return_value = {"assets": 0, "findings": 0}

    monkeypatch.setattr(
        "connectors.microsoft_entra_id.push.PlatformClient",
        lambda: created,
    )

    result = push_to_platform(assets=[], findings=[])

    created.push.assert_called_once_with([], [])
    assert result == {"assets": 0, "findings": 0}
