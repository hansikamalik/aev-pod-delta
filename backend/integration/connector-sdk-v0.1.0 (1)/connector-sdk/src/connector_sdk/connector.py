"""The mandatory ``Connector`` base class.

Contract references:
  - Section 3  (Mandatory Connector Interface)
  - Section 4  (Connector Name)
  - Section 10 (discover)
  - Section 11 (ingest)
  - Section 13 (sync)
  - Section 17 (check_health)
  - Section 18/19 (config + credential contracts)

Every connector MUST extend this class. The public method names and return
types below are authoritative and MUST NOT be changed by an implementation.

Minimal implementation::

    class AzureConnector(Connector):
        name = "azure"

        def discover(self):
            for vm in self._client.list_vms():
                yield Asset(
                    id=vm["id"],
                    source=self.name,
                    type=AssetType.COMPUTE,
                    name=vm["name"],
                    raw=vm,
                )

        def ingest(self, assets):
            assets = list(assets)
            self._platform.bulk_upsert([a.to_dict() for a in assets])
            return len(assets)

        def check_health(self) -> bool: ...
        def describe_config(self) -> dict: ...
        def describe_credentials(self) -> dict: ...

``sync()`` is provided by the SDK and SHOULD NOT be overridden.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Iterable, Iterator, Mapping

from .exceptions import (
    ConnectorError,
    ContractViolation,
    IngestionError,
    ValidationError,
)
from .enums import SyncStatus
from .models import Asset, SyncResult, utcnow
from .schemas import (
    assert_valid_schema,
    redact,
    validate_against_schema,
)

logger = logging.getLogger(__name__)

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class Connector(ABC):
    """Base class every connector must extend.

    Parameters
    ----------
    config:
        Non-secret configuration matching :meth:`describe_config`.
    credentials:
        Secret values matching :meth:`describe_credentials`. Never logged.

    Subclasses that define their own ``__init__`` MUST call
    ``super().__init__(config=..., credentials=...)``.
    """

    #: Stable, unique, lowercase source identifier (Section 4).
    #: Override as a class attribute (``name = "azure"``) or as a property.
    name: str = ""

    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        credentials: Mapping[str, Any] | None = None,
    ) -> None:
        self._config: dict[str, Any] = dict(config or {})
        self._credentials: dict[str, Any] = dict(credentials or {})
        self._assert_name_valid()

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------

    def _assert_name_valid(self) -> None:
        name = self.name
        if not isinstance(name, str) or not name.strip():
            raise ContractViolation(
                f"{type(self).__name__} must define a non-empty 'name' (Section 4)"
            )
        if not _NAME_PATTERN.match(name):
            raise ContractViolation(
                f"Connector name {name!r} must be lowercase alphanumeric with underscores, "
                "must not embed environment or version information (Section 4)"
            )

    # ------------------------------------------------------------------
    # Config / credentials
    # ------------------------------------------------------------------

    @property
    def config(self) -> Mapping[str, Any]:
        """Validated non-secret configuration."""
        return dict(self._config)

    @property
    def safe_credentials(self) -> dict[str, Any]:
        """Credentials with every secret redacted. Safe to log."""
        try:
            schema = self.describe_credentials()
        except Exception:  # pragma: no cover - defensive
            schema = {}
        return redact(self._credentials, schema)

    def get_credential(self, key: str) -> Any:
        """Read a single credential. Prefer this over touching ``_credentials``."""
        return self._credentials.get(key)

    def validate_configuration(self) -> None:
        """Validate config and credentials against their declared schemas.

        Call before authenticating. Raises :class:`ConfigurationError` or
        :class:`CredentialError`. Error messages never contain secret values.
        """
        config_schema = self.describe_config()
        credential_schema = self.describe_credentials()

        assert_valid_schema(config_schema, kind="config")
        assert_valid_schema(credential_schema, kind="credentials")

        validate_against_schema(self._config, config_schema, kind="config")
        validate_against_schema(self._credentials, credential_schema, kind="credentials")

    # ------------------------------------------------------------------
    # Mandatory interface
    # ------------------------------------------------------------------

    @abstractmethod
    def discover(self) -> Iterable[Asset]:
        """Read resources from the source system and yield normalized assets.

        MUST return only valid :class:`Asset` objects, set ``source`` to
        ``self.name``, use stable IDs, normalize the asset type, preserve
        the raw payload, and handle pagination.

        MUST NOT push assets, modify platform state, call :meth:`ingest`,
        or silently discard API failures.
        """

    @abstractmethod
    def ingest(self, assets: Iterable[Asset]) -> int:
        """Push normalized assets to the platform and return the pushed count.

        MUST return the number of *successfully* pushed assets — an asset
        rejected by the platform MUST NOT be counted.
        """

    @abstractmethod
    def check_health(self) -> bool:
        """Lightweight reachability + credential check (Section 17).

        Returns ``True`` only when the source is reachable with the
        configured credentials. MUST NOT discover or ingest.
        """

    @abstractmethod
    def describe_config(self) -> dict:
        """JSON-Schema-shaped dict of non-secret configuration (Section 18)."""

    @abstractmethod
    def describe_credentials(self) -> dict:
        """JSON-Schema-shaped dict of required secrets (Section 19)."""

    # ------------------------------------------------------------------
    # SDK-provided validation wrapper
    # ------------------------------------------------------------------

    def discover_validated(self) -> Iterator[Asset]:
        """Wrap :meth:`discover`, enforcing the asset-level contract.

        Yields each asset after checking that it is an :class:`Asset`, that
        ``asset.source == self.name`` (Section 7), and that asset IDs are
        unique within the run. Used by :meth:`sync`.
        """
        seen: set[str] = set()
        for asset in self.discover():
            if not isinstance(asset, Asset):
                raise ContractViolation(
                    f"{type(self).__name__}.discover() yielded {type(asset).__name__}, "
                    "expected Asset",
                    operation="discover",
                    source=self.name,
                )
            if asset.source != self.name:
                raise ContractViolation(
                    f"Asset source {asset.source!r} does not match connector name "
                    f"{self.name!r} (Section 7)",
                    operation="discover",
                    source=self.name,
                    resource_id=asset.id,
                )
            if asset.id in seen:
                raise ContractViolation(
                    f"Duplicate asset id {asset.id!r} within a single discovery run",
                    operation="discover",
                    source=self.name,
                    resource_id=asset.id,
                )
            seen.add(asset.id)
            yield asset

    # ------------------------------------------------------------------
    # sync()
    # ------------------------------------------------------------------

    async def sync(self) -> SyncResult:
        """Default synchronization: discover -> ingest -> SyncResult.

        Status is derived per Section 15: everything pushed with no errors is
        ``success``; a short push count or recorded errors is ``partial``;
        a failure to push anything that was discovered is ``failed``.

        Override only for a documented reason (incremental sync,
        checkpointing, custom batching, retry orchestration) and preserve
        this :class:`SyncResult` contract.
        """
        started_at = utcnow()
        result = SyncResult(connector=self.name, status=SyncStatus.FAILED, started_at=started_at)

        try:
            assets = list(self.discover_validated())
            result.assets_discovered = len(assets)

            if not assets:
                logger.info("connector=%s discovered no assets", self.name)
                result.assets_pushed = 0
                result.status = SyncResult.derive_status(
                    discovered=0, pushed=0, errors=result.errors
                )
                return result

            pushed = self.ingest(assets)
            result.assets_pushed = self._coerce_pushed_count(pushed, len(assets))

            if result.assets_pushed < result.assets_discovered:
                result.add_error(
                    IngestionError(
                        f"{result.assets_discovered - result.assets_pushed} of "
                        f"{result.assets_discovered} asset(s) were not pushed",
                        operation="ingest",
                        source=self.name,
                    )
                )

            result.status = SyncResult.derive_status(
                discovered=result.assets_discovered,
                pushed=result.assets_pushed,
                errors=result.errors,
            )
            return result

        except ConnectorError as exc:
            logger.error(
                "connector=%s sync failed operation=%s", self.name, exc.operation or "unknown"
            )
            result.add_error(exc)
            result.status = SyncStatus.FAILED
            return result

        except Exception as exc:  # noqa: BLE001 - boundary: must never leak
            logger.exception("connector=%s sync raised an unexpected error", self.name)
            result.add_error(
                ConnectorError(
                    f"Unexpected {type(exc).__name__} during sync: {exc}",
                    operation="sync",
                    source=self.name,
                )
            )
            result.status = SyncStatus.FAILED
            return result

        finally:
            # Stamp completion and coerce status into the enum, whatever
            # path we exited through.
            result.finalize()

    def _coerce_pushed_count(self, pushed: Any, discovered: int) -> int:
        """Validate the value returned by :meth:`ingest`."""
        if isinstance(pushed, bool) or not isinstance(pushed, int):
            raise ContractViolation(
                f"{type(self).__name__}.ingest() must return an int, "
                f"got {type(pushed).__name__} (Section 11)",
                operation="ingest",
                source=self.name,
            )
        if pushed < 0:
            raise ContractViolation(
                "ingest() returned a negative count",
                operation="ingest",
                source=self.name,
            )
        if pushed > discovered:
            raise ContractViolation(
                f"ingest() reported {pushed} pushed but only {discovered} were discovered",
                operation="ingest",
                source=self.name,
            )
        return pushed

    def sync_blocking(self) -> SyncResult:
        """Run :meth:`sync` from synchronous code.

        Convenience for cron jobs, CLI entry points, and tests. Raises if
        called from inside a running event loop — ``await sync()`` there.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.sync())
        raise RuntimeError(
            "sync_blocking() cannot be called from a running event loop; await sync() instead"
        )

    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<{type(self).__name__} name={self.name!r}>"


__all__ = ["Connector"]
