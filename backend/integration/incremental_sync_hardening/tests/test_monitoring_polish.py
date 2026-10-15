import pytest
from monitoring.metrics_alerter import MetricsAlerter
from monitoring.monitoring_api import SyncMonitoringAPI


def test_metrics_alerter_success_and_failure():
    alerter = MetricsAlerter(alert_channel="#sec-alerts")
    
    success_res = alerter.report_sync_success("test_connector", "users", 0.8, 10)
    assert success_res["status"] == "SUCCESS"
    assert success_res["records_pushed"] == 10

    fail_res = alerter.report_sync_failure("test_connector", "Token expired")
    assert fail_res["alert_level"] == "CRITICAL"
    assert "#sec-alerts" in fail_res["channel"]


def test_sync_monitoring_api_telemetry():
    api = SyncMonitoringAPI()
    api.record_sync_event("conn_a", "success", 1.0, 50)
    api.record_sync_event("conn_b", "failed", 0.5, 0, error="Auth failed")

    status_a = api.get_connector_status("conn_a")
    assert status_a["last_status"] == "success"
    assert status_a["total_syncs"] == 1

    fleet = api.get_fleet_telemetry()
    assert fleet["total_sync_executions"] == 2
    assert fleet["active_critical_alerts"] == 1
    assert fleet["fleet_success_rate_percent"] == 50.0
