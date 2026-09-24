from typing import Iterable, Optional, Union
from connector_sdk.connector import Connector
from connector_sdk.models import Asset, Checkpoint
from client import SplunkClient
from config import get_config_schema, get_credentials_schema
from models import normalize_splunk_event_to_asset


class SplunkConnector(Connector):

    name = "splunk"

    def __init__(self, config: dict, credentials: dict, platform_client=None):
        super().__init__(config, credentials, platform_client)
        self._client = SplunkClient(
            host=config["host"],
            bearer_token=credentials["bearer_token"],
            port=config.get("port", 8089),
            verify_ssl=config.get("verify_ssl", True)
        )

    def describe_config(self) -> dict:
        return get_config_schema()

    def describe_credentials(self) -> dict:
        return get_credentials_schema()

    def check_health(self) -> bool:
        return self._client.ping()

    def discover(
        self, checkpoint: Optional[Checkpoint] = None
    ) -> Iterable[Union[Asset, Checkpoint]]:
        batch_size = self.config.get("batch_size", 100)
        search_query = self.config.get("search_query", "search index=_internal")

        earliest_time = None
        if checkpoint and checkpoint.last_sync_timestamp:
            earliest_time = checkpoint.last_sync_timestamp.strftime("%Y-%m-%dT%H:%M:%S")

        sid = self._client.create_search_job(query=search_query, earliest_time=earliest_time)
        results = self._client.get_search_results(sid=sid, count=batch_size)

        latest_timestamp = checkpoint.last_sync_timestamp if checkpoint else None

        for event in results:
            asset = normalize_splunk_event_to_asset(event, self.name)
            
            if not latest_timestamp or asset.discoveredAt > latest_timestamp:
                latest_timestamp = asset.discoveredAt

            yield asset

        if latest_timestamp:
            yield Checkpoint(
                connector=self.name,
                last_sync_timestamp=latest_timestamp,
                metadata={"last_sid": sid}
            )

    def ingest(self, assets: Iterable[Asset]) -> int:
        asset_list = list(assets)
        if not asset_list:
            return 0

        raw_payloads = [asset.raw for asset in asset_list]
        self._client.forward_events(raw_payloads)

        if self.platform_client and hasattr(self.platform_client, "bulk_upsert"):
            self.platform_client.bulk_upsert(asset_list)

        return len(asset_list)
