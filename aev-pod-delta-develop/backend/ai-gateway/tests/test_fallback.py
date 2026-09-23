from unittest.mock import patch
import app.client as client
from app.client import FallbackMonitor, ask_gpt


def test_fallback_monitor_records_and_prunes():
    monitor = FallbackMonitor(spike_threshold=3, window_seconds=60)
    is_spike = monitor.record_fallback("google_gemma", "mock", "500 Internal Error")
    assert is_spike is False
    assert len(monitor.fallback_timestamps) == 1


def test_fallback_monitor_triggers_spike_alert():
    monitor = FallbackMonitor(spike_threshold=3, window_seconds=60)
    monitor.record_fallback("google_gemma", "mock", "Error 1")
    monitor.record_fallback("google_gemma", "mock", "Error 2")
    is_spike = monitor.record_fallback("google_gemma", "mock", "Error 3")
    assert is_spike is True


def test_ask_gpt_returns_fallback_metadata_on_failure():
    with patch.object(client, "USE_GEMMA_GOOGLE", True), \
         patch.object(client, "USE_COLAB_GEMMA", False), \
         patch.object(client, "_ask_gemma", side_effect=RuntimeError("Google API 503 Outage")):
        result = ask_gpt("What is SIEM?")
        assert result["model"] == "mock"
        assert result["fallback"] is True
        assert "Google API 503 Outage" in result["fallback_reason"]


def test_ask_gpt_mock_mode_default_metadata():
    with patch.object(client, "USE_GEMMA_GOOGLE", False), \
         patch.object(client, "USE_COLAB_GEMMA", False):
        result = ask_gpt("Explain firewall")
        assert result["model"] == "mock"
        assert result["fallback"] is False
