"""<source> connector. Copy, rename, and replace every TODO."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from connector_sdk import (
    Asset,
    AssetType,
    Connector,
    DiscoveryError,
    field,
    object_schema,
    secret_field,
)

# TODO: map source resource kinds onto normalized categories.
_TYPE_MAP: dict[str, AssetType] = {}


class TemplateConnector(Connector):
    name = "template"  # TODO: stable, lowercase, no env or version

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        credentials: Mapping[str, Any] | None = None,
        *,
        client: Any | None = None,
        platform_client: Any | None = None,
    ) -> None:
        super().__init__(config=config, credentials=credentials)
        self._client = client  # TODO: build the real client
        self._platform = platform_client

    def describe_config(self) -> dict:
        # TODO: non-secret config only.
        return object_schema({"region": field("string")}, required=["region"])

    def describe_credentials(self) -> dict:
        # TODO: every field must be a secret_field().
        return object_schema({"api_key": secret_field()}, required=["api_key"])

    def check_health(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    def discover(self) -> Iterable[Asset]:
        try:
            for resource in self._client.iter_resources():  # TODO: paginate
                yield Asset(
                    id=resource["id"],
                    source=self.name,
                    type=_TYPE_MAP.get(resource.get("kind", ""), AssetType.OTHER),
                    name=resource["name"],
                    raw=resource,
                )
        except Exception as exc:
            raise DiscoveryError(
                f"Discovery failed: {exc}", operation="discover", source=self.name
            ) from exc

    def ingest(self, assets: Iterable[Asset]) -> int:
        assets = list(assets)
        if not assets:
            return 0
        # TODO: batch, and return only what the platform accepted.
        return int(self._platform.bulk_upsert(assets))
