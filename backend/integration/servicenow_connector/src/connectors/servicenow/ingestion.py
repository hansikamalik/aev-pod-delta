"""Ingestion stage: stream raw ServiceNow records for downstream normalization."""

from __future__ import annotations

from typing import Any, Dict, Iterator, Tuple

from .client import ServiceNowClient
from .discovery import CMDB_FIELDS, INCIDENT_FIELDS


def ingest(
    client: ServiceNowClient,
    tables_cfg: Dict[str, str],
    batch_size: int = 200,
) -> Tuple[Iterator[Dict[str, Any]], Iterator[Dict[str, Any]]]:
    """Return (asset_records, finding_records) iterators."""
    assets = client.get_table(
        tables_cfg["cmdb_ci"],
        params={"sysparm_fields": CMDB_FIELDS},
        batch_size=batch_size,
    )
    findings = client.get_table(
        tables_cfg["incident"],
        params={"sysparm_fields": INCIDENT_FIELDS},
        batch_size=batch_size,
    )
    return assets, findings
