import time
from typing import Dict, Any, List


class SyncMonitoringAPI:
    """Polished monitoring API providing real-time telemetry, health status, and alert aggregation."""

    def __init__(self):
        self._metrics_history: List[Dict[str, Any]] = []
        self._active_alerts: List[Dict[str, Any]] = []

    def record_sync_event(self, connector_id: str, status: str, duration: float, records_pushed: int, error: str = "") -> None:
        event = {
            "connector_id": connector_id,
            "status": status,
            "duration_seconds": duration,
            "records_pushed": records_pushed,
            "timestamp": time.time()
        }
        self._metrics_history.append(event)
        if status.lower() == "failed":
            self._active_alerts.append({
                "connector_id": connector_id,
                "error": error,
                "timestamp": time.time()
            })

    def get_connector_status(self, connector_id: str) -> Dict[str, Any]:
        connector_events = [e for e in self._metrics_history if e["connector_id"] == connector_id]
        if not connector_events:
            return {"connector_id": connector_id, "status": "UNKNOWN", "total_syncs": 0}
        
        last_event = connector_events[-1]
        return {
            "connector_id": connector_id,
            "last_status": last_event["status"],
            "last_duration_sec": last_event["duration_seconds"],
            "total_syncs": len(connector_events)
        }

    def get_fleet_telemetry(self) -> Dict[str, Any]:
        total_syncs = len(self._metrics_history)
        failed_syncs = len(self._active_alerts)
        success_rate = ((total_syncs - failed_syncs) / total_syncs * 100) if total_syncs > 0 else 100.0
        return {
            "total_sync_executions": total_syncs,
            "active_critical_alerts": failed_syncs,
            "fleet_success_rate_percent": round(success_rate, 2),
            "alerts": self._active_alerts
        }
