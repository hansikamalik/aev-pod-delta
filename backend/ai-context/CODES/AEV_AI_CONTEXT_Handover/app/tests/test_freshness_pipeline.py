"""
Unit and integration tests for P1-4: Real-Time Vector Freshness Event Pipeline (60s SLA).
Tests AssetUpdated, ExposureDetected, RiskCalculated event processing,
SLA lag calculation (within_sla vs sla_breached), metrics aggregation,
Redis pub/sub integration, and FastAPI HTTP ingestion endpoints.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.freshness_pipeline import VectorFreshnessPipeline, freshness_pipeline
from app.main import app

ADMIN_API_KEY = "freshness-pipeline-admin-key-32chars-min-test"


@pytest.fixture(autouse=True)
def setup_pipeline_env(monkeypatch):
    """Ensure clean pipeline state and test authentication."""
    monkeypatch.setenv(
        "AEV_API_KEYS_JSON",
        json.dumps({
            ADMIN_API_KEY: {"user_id": "admin_user", "role": "admin", "tenant_id": "tenant-secops"}
        }),
    )
    monkeypatch.setenv("AEV_DATA_SOURCE", "mock")
    freshness_pipeline.reset_metrics()
    yield
    freshness_pipeline.reset_metrics()


class TestVectorFreshnessPipelineCore:
    """Test core vector freshness processing and 60-second SLA logic."""

    def test_process_asset_updated_event_within_sla(self):
        pipeline = VectorFreshnessPipeline()
        # Event occurred 5 seconds ago
        event_time = datetime.now(timezone.utc) - timedelta(seconds=5)
        event = {
            "event_type": "AssetUpdated",
            "asset_id": 101,
            "timestamp": event_time.isoformat(),
            "changes": {
                "asset_name": "prod-k8s-cluster-01",
                "operating_system": "Linux 6.8",
                "description": "Production Kubernetes master node running mission-critical workloads",
            },
        }

        result = pipeline.process_event(event)

        assert result["status"] == "success"
        assert result["asset_id"] == 101
        assert result["event_type"] == "AssetUpdated"
        assert result["within_sla"] is True
        assert result["freshness_status"] == "within_sla"
        assert 4.0 <= result["measured_lag_seconds"] <= 10.0
        assert result["sla_target_seconds"] == 60
        assert result["embedding_dimension"] == 384

    def test_process_risk_calculated_event_within_sla(self):
        pipeline = VectorFreshnessPipeline()
        event_time = datetime.now(timezone.utc) - timedelta(seconds=2)
        event = {
            "event_type": "RiskCalculated",
            "asset_id": 102,
            "risk_score": 92,
            "timestamp": event_time.isoformat(),
            "description": "Critical risk score updated following threat actor exposure scan",
        }

        result = pipeline.process_event(event)

        assert result["status"] == "success"
        assert result["asset_id"] == 102
        assert result["within_sla"] is True
        assert result["measured_lag_seconds"] <= 60.0

    def test_process_exposure_detected_event_within_sla(self):
        pipeline = VectorFreshnessPipeline()
        event = {
            "event_type": "ExposureDetected",
            "asset_id": 103,
            "exposure_type": "CVE-2026-2819",
            "severity": "CRITICAL",
            "description": "Unauthenticated remote code execution vulnerability detected on public gateway",
            "risk_score": 95,
        }

        result = pipeline.process_event(event)

        assert result["status"] == "success"
        assert result["asset_id"] == 103
        assert result["within_sla"] is True
        assert result["freshness_status"] == "within_sla"

    def test_process_event_sla_breached_when_lag_exceeds_60s(self):
        pipeline = VectorFreshnessPipeline()
        # Event occurred 75 seconds ago -> should exceed 60s SLA
        event_time = datetime.now(timezone.utc) - timedelta(seconds=75)
        event = {
            "event_type": "AssetUpdated",
            "asset_id": 104,
            "timestamp": event_time.isoformat(),
            "description": "Legacy mainframe patch event",
        }

        result = pipeline.process_event(event)

        assert result["status"] == "success"
        assert result["within_sla"] is False
        assert result["freshness_status"] == "sla_breached"
        assert result["measured_lag_seconds"] >= 74.0

    def test_pipeline_aggregate_metrics(self):
        pipeline = VectorFreshnessPipeline()

        # Ingest 2 events within SLA
        pipeline.process_event({
            "event_type": "AssetUpdated",
            "asset_id": 1,
            "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(),
        })
        pipeline.process_event({
            "event_type": "RiskCalculated",
            "asset_id": 2,
            "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
        })

        # Ingest 1 event that breached SLA (70s lag)
        pipeline.process_event({
            "event_type": "ExposureDetected",
            "asset_id": 3,
            "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=70)).isoformat(),
        })

        metrics = pipeline.get_metrics()
        assert metrics["total_events_processed"] == 3
        assert metrics["events_within_sla"] == 2
        assert metrics["events_sla_breached"] == 1
        assert metrics["sla_compliance_pct"] == round((2 / 3) * 100.0, 2)
        assert metrics["max_lag_seconds"] >= 69.0
        assert metrics["status"] == "degraded"


class TestRedisPubSubIntegration:
    """Test Redis publication and subscription handling."""

    def test_publish_event_via_redis_client(self):
        pipeline = VectorFreshnessPipeline()
        mock_client = MagicMock()

        event = {"event_type": "AssetUpdated", "asset_id": 201, "timestamp": datetime.now(timezone.utc).isoformat()}
        ok = pipeline.publish_event(event, redis_client=mock_client)

        assert ok is True
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args[0]
        assert call_args[0] == pipeline.channel
        payload = json.loads(call_args[1])
        assert payload["asset_id"] == 201

    def test_redis_listener_worker_processes_incoming_message(self):
        pipeline = VectorFreshnessPipeline()
        mock_client = MagicMock()
        mock_pubsub = MagicMock()
        mock_client.pubsub.return_value = mock_pubsub

        test_event = {
            "event_type": "AssetUpdated",
            "asset_id": 305,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # First call returns a message, subsequent calls return None
        messages = [{"type": "message", "data": json.dumps(test_event)}, None]

        def get_msg_side_effect(*args, **kwargs):
            if messages:
                return messages.pop(0)
            pipeline.stop_redis_listener()
            return None

        mock_pubsub.get_message.side_effect = get_msg_side_effect

        ok = pipeline.start_redis_listener(redis_client=mock_client)
        assert ok is True

        # Let the thread run briefly to process
        import time
        time.sleep(0.1)
        pipeline.stop_redis_listener()

        metrics = pipeline.get_metrics()
        assert metrics["total_events_processed"] >= 1


class TestHttpEndpoints:
    """Test HTTP API endpoints for event ingestion and freshness reporting."""

    def test_http_ingest_single_event(self):
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}
        payload = {
            "event_type": "AssetUpdated",
            "asset_id": 1,
            "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=8)).isoformat(),
            "changes": {"asset_name": "firewall-edge-01"},
        }

        response = client.post("/events/ingest", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["within_sla"] is True
        assert data["result"]["freshness_status"] == "within_sla"
        assert data["pipeline_metrics"]["total_events_processed"] >= 1

    def test_http_ingest_batch_events(self):
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}
        payload = {
            "events": [
                {
                    "event_type": "AssetUpdated",
                    "asset_id": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "event_type": "RiskCalculated",
                    "asset_id": 2,
                    "risk_score": 88,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            ]
        }

        response = client.post("/events/ingest", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["batch_size"] == 2
        assert len(data["results"]) == 2

    def test_http_get_copilot_freshness_metrics_includes_pipeline(self):
        client = TestClient(app)
        headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}

        response = client.get("/copilot/freshness-metrics", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "pipeline_metrics" in data
        assert data["sla_seconds"] == 60
        assert "total_assets" in data
