import logging
from typing import Dict, Any

logger = logging.getLogger("SyncEngineAlerts")


class MetricsAlerter:
    """Tracks sync metrics, duration, record counts, and routes failure alerts to team channels."""

    def __init__(self, alert_channel: str = "#sec-sync-alerts"):
        self.alert_channel = alert_channel

    def report_sync_success(self, connector_id: str, resource_type: str, duration_seconds: float, record_count: int) -> Dict[str, Any]:
        metrics = {
            "connector": connector_id,
            "resource": resource_type,
            "status": "SUCCESS",
            "duration_sec": duration_seconds,
            "records_pushed": record_count
        }
        logger.info(f"[METRICS SUCCESS] {connector_id} | {metrics}")
        return metrics

    def report_sync_failure(self, connector_id: str, error_message: str) -> Dict[str, Any]:
        alert_payload = {
            "channel": self.alert_channel,
            "connector": connector_id,
            "alert_level": "CRITICAL",
            "message": f"Sync failure detected: {error_message}"
        }
        logger.error(f"[ALERT ROUTED TO {self.alert_channel}] {alert_payload}")
        return alert_payload
