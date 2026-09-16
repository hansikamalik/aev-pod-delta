import os
import shutil
import pytest
import requests_mock
from src.push.platform_pusher import PlatformPushEngine


class TestPlatformPushEngineUnit:

    @pytest.fixture(autouse=True)
    def setup_dlq(self):
        self.test_dlq_dir = "tests/test_dlq_output"
        os.makedirs(self.test_dlq_dir, exist_ok=True)
        yield
        if os.path.exists(self.test_dlq_dir):
            shutil.rmtree(self.test_dlq_dir)

    def test_push_batch_success_200(self, requests_mock):
        endpoint = "https://platform.api.com/v1/assets"
        requests_mock.post(endpoint, status_code=200, json={"status": "accepted"})

        pusher = PlatformPushEngine(
            endpoint_url=endpoint,
            api_key="test-key",
            batch_size=10,
            dlq_dir=self.test_dlq_dir
        )
        sample_assets = [{"asset_id": f"asset-{i}"} for i in range(5)]
        
        result = pusher.push_batch(sample_assets)
        assert result["successful"] == 5
        assert result["failed"] == 0
        assert len(result["dlq_files"]) == 0

    def test_push_batch_http_429_retries_and_routes_to_dlq(self, requests_mock):
        endpoint = "https://platform.api.com/v1/assets"
        # Simulate continuous Rate Limit (HTTP 429)
        requests_mock.post(endpoint, status_code=429, json={"error": "Rate limited"})

        pusher = PlatformPushEngine(
            endpoint_url=endpoint,
            api_key="test-key",
            batch_size=10,
            max_retries=2,
            base_backoff_sec=0.01,  # Speed up tests
            dlq_dir=self.test_dlq_dir
        )
        sample_assets = [{"asset_id": "failed-asset-1"}]

        result = pusher.push_batch(sample_assets)
        assert result["successful"] == 0
        assert result["failed"] == 1
        assert len(result["dlq_files"]) == 1
        assert os.path.exists(result["dlq_files"][0])

    def test_push_batch_http_500_retries_and_routes_to_dlq(self, requests_mock):
        endpoint = "https://platform.api.com/v1/assets"
        # Simulate Internal Server Error (HTTP 500)
        requests_mock.post(endpoint, status_code=500, json={"error": "Server error"})

        pusher = PlatformPushEngine(
            endpoint_url=endpoint,
            api_key="test-key",
            batch_size=5,
            max_retries=2,
            base_backoff_sec=0.01,
            dlq_dir=self.test_dlq_dir
        )
        sample_assets = [{"asset_id": "failed-asset-500"}]

        result = pusher.push_batch(sample_assets)
        assert result["failed"] == 1
        assert len(result["dlq_files"]) == 1
