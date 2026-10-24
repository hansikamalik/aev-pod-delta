"""Discovery stage: enumerate the tables and record counts this connector owns."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .client import ServiceNowClient


CMDB_FIELDS = (
    "sys_id,name,sys_class_name,ip_address,fqdn,os,operating_system,"
    "environment,u_environment,assigned_to,owned_by,sys_created_on"
)
INCIDENT_FIELDS = (
    "sys_id,number,short_description,description,severity,impact,state,"
    "cmdb_ci,opened_at,sys_created_on,sys_updated_on"
)


@dataclass
class DiscoveryResult:
    tables: Dict[str, str] = field(default_factory=dict)        # table -> display name
    fields: Dict[str, str] = field(default_factory=dict)        # table -> sysparm_fields
    estimated_counts: Dict[str, int] = field(default_factory=dict)
    checks: List[str] = field(default_factory=list)


def discover(client: ServiceNowClient, tables_cfg: Dict[str, str]) -> DiscoveryResult:
    """Probe the configured tables; record counts via HEAD-style limit-1 probe.

    A table that errors is recorded as 0 and noted in `checks` so a partial
    outage does not kill the whole sync.
    """
    result = DiscoveryResult(
        tables=dict(tables_cfg),
        fields={"cmdb_ci": CMDB_FIELDS, "incident": INCIDENT_FIELDS},
    )
    for key, table in tables_cfg.items():
        try:
            pages = client.get_table(
                table, params={"sysparm_fields": "sys_id", "sysparm_limit": 1}, batch_size=1
            )
            count = 0
            for _ in pages:
                count = 1  # table reachable; exact count is not required for discovery
            result.estimated_counts[table] = count
        except Exception as exc:  # noqa: BLE001 - discovery must be fault tolerant
            result.estimated_counts[table] = 0
            result.checks.append(f"table {table} unreachable: {exc}")
    return result
