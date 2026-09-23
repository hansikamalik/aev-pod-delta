from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from elastic_connector.client import ElasticClient
from elastic_connector.config import ElasticConfig, ElasticCredentials
from elastic_connector.models import Asset, AssetType, SyncResult


class Connector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def discover(self) -> Iterable[Asset]:
        ...

    @abstractmethod
    def ingest(self, assets: Iterable[Asset]) -> int:
        ...

    @abstractmethod
    def check_health(self) -> bool:
        ...

    @abstractmethod
    def describe_config(self) -> dict:
        ...

    @abstractmethod
    def describe_credentials(self) -> dict:
        ...


class ElasticConnector(Connector):
    name = "elastic"

    def __init__(self, config: Dict[str, Any], credentials: Dict[str, Any], platform_client: Optional[Any] = None):
        self._config = ElasticConfig(**config)
        self._credentials = ElasticCredentials(**credentials)
        self._client = ElasticClient(
            endpoint=self._config.endpoint,
            api_key=self._credentials.api_key,
            timeout=self._config.timeout,
            verify_ssl=self._config.verify_ssl,
        )
        self._platform_client = platform_client

    def check_health(self) -> bool:
        return self._client.ping()

    def describe_config(self) -> dict:
        return ElasticConfig.model_json_schema()

    def describe_credentials(self) -> dict:
        return ElasticCredentials.model_json_schema()

    def discover(self) -> Iterable[Asset]:
        # 1. Discover Compute Assets (Cluster Nodes)
        try:
            nodes = self._client.list_nodes()
            for node in nodes:
                node_id = str(node.get("node_id", "unknown"))
                node_name = str(node.get("name", f"node-{node_id}"))
                yield Asset(
                    id=f"elastic:node:{node_id}",
                    source=self.name,
                    type=AssetType.COMPUTE,
                    name=node_name,
                    raw=node,
                    tags={
                        "ip": str(node.get("ip", "")),
                        "version": str(node.get("version", ""))
                    }
                )
        except Exception:
            pass

        # 2. Discover Storage Assets (Indices)
        try:
            indices = self._client.list_indices()
            for idx in indices:
                idx_name = str(idx.get("index", "unknown"))
                yield Asset(
                    id=f"elastic:index:{idx_name}",
                    source=self.name,
                    type=AssetType.STORAGE,
                    name=idx_name,
                    raw=idx,
                    tags={
                        "health": str(idx.get("health", "")),
                        "status": str(idx.get("status", ""))
                    }
                )
        except Exception:
            pass

        # 3. Discover Detection Assets (Transforms / Analytics Jobs)
        try:
            transforms = self._client.list_transforms()
            for tf in transforms:
                tf_id = str(tf.get("id", "unknown"))
                yield Asset(
                    id=f"elastic:transform:{tf_id}",
                    source=self.name,
                    type=AssetType.DETECTION,
                    name=tf_id,
                    raw=tf
                )
        except Exception:
            pass

    def ingest(self, assets: Iterable[Asset]) -> int:
        asset_list = list(assets)
        if self._platform_client:
            self._platform_client.bulk_upsert(asset_list)
        return len(asset_list)

    async def sync(self) -> SyncResult:
        started_at = datetime.now(timezone.utc)
        errors: List[Dict[str, Any]] = []
        discovered_assets: List[Asset] = []

        try:
            discovered_assets = list(self.discover())
            pushed_count = self.ingest(discovered_assets)
            status = "success"
        except Exception as exc:
            status = "failed"
            pushed_count = 0
            errors.append({
                "operation": "sync",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        return SyncResult(
            connector=self.name,
            status=status,
            assets_discovered=len(discovered_assets),
            assets_pushed=pushed_count,
            errors=errors,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc)
        )
