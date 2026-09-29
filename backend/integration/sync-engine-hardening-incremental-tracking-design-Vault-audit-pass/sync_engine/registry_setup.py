"""
Wires every connector into the SyncRegistry so sync_all_connectors() can
run them all in one pass.

TODO (fill in before this is used for real):
  Each commented-out import below is a placeholder. Replace it with the
  actual fetch function each connector exposes (its discover()/ingest()
  or equivalent), then uncomment the matching registry.register() call.

  To find the right function in each connector folder, run:
      Select-String -Path .\*\*.py -Pattern "def discover|def ingest|def fetch_events" `
          | Select-Object Path, LineNumber, Line

  If a connector's function signature doesn't match
  `async def fn(start_time: str, end_time: str) -> list`, wrap it in a
  small adapter here rather than changing engine.py.
"""

from sync_engine.orchestrator import ConnectorSyncConfig, SyncRegistry

# from jira_connector.sync import fetch_events as fetch_jira
# from microsoft_defender_connector.sync import fetch_events as fetch_defender
# from microsoft365_connector.sync import fetch_events as fetch_m365
# from okta_connector.sync import fetch_events as fetch_okta
# from qradar_connector.sync import fetch_events as fetch_qradar
# from servicenow_connector.sync import fetch_events as fetch_servicenow
# from splunk_connector.sync import fetch_events as fetch_splunk


def build_default_registry() -> SyncRegistry:
    registry = SyncRegistry()

    # registry.register(ConnectorSyncConfig(
    #     connector_id="jira",
    #     fetch_events_fn=fetch_jira,
    #     default_lookback_days=7,
    # ))
    # registry.register(ConnectorSyncConfig(
    #     connector_id="microsoft-defender",
    #     fetch_events_fn=fetch_defender,
    #     default_lookback_days=7,
    # ))
    # registry.register(ConnectorSyncConfig(
    #     connector_id="microsoft365",
    #     fetch_events_fn=fetch_m365,
    #     default_lookback_days=3,
    # ))
    # registry.register(ConnectorSyncConfig(
    #     connector_id="okta",
    #     fetch_events_fn=fetch_okta,
    #     default_lookback_days=7,
    # ))
    # registry.register(ConnectorSyncConfig(
    #     connector_id="qradar",
    #     fetch_events_fn=fetch_qradar,
    #     default_lookback_days=7,
    # ))
    # registry.register(ConnectorSyncConfig(
    #     connector_id="servicenow",
    #     fetch_events_fn=fetch_servicenow,
    #     default_lookback_days=7,
    # ))
    # registry.register(ConnectorSyncConfig(
    #     connector_id="splunk",
    #     fetch_events_fn=fetch_splunk,
    #     default_lookback_days=7,
    # ))

    return registry


if __name__ == "__main__":
    import asyncio
    from sync_engine.orchestrator import sync_all_connectors

    class _PlaceholderPlatformClient:
        """Swap this for the real platform client before running for real."""
        def __init__(self):
            self._checkpoints = {}

        def get_checkpoint(self, connector_id):
            return self._checkpoints.get(connector_id)

        def save_checkpoint(self, checkpoint):
            self._checkpoints[checkpoint.connector] = checkpoint

        def push_assets(self, assets):
            print(f"push_assets called with {len(assets)} assets")

    registry = build_default_registry()
    client = _PlaceholderPlatformClient()
    results = asyncio.run(sync_all_connectors(registry, client))
    for name, result in results.items():
        print(name, result.status, result.assets_pushed)
