
"""Shared mock data for workflow_assist and integration_list tools."""

from typing import Any, Dict, List


WORKFLOWS: Dict[str, Dict[str, Any]] = {
    "rotate_credentials": {
        "workflow_id": "rotate_credentials",
        "description": "Rotate credentials for a specified asset.",
        "required_params": ["asset_id"],
    },
    "isolate_host": {
        "workflow_id": "isolate_host",
        "description": "Isolate a host from the network.",
        "required_params": ["host_id"],
    },
    "rescan_asset": {
        "workflow_id": "rescan_asset",
        "description": "Run a vulnerability rescan against an asset.",
        "required_params": ["asset_id"],
    },
}

INTEGRATIONS: List[Dict[str, Any]] = [
    {"name": "Microsoft Defender", "status": "connected"},
    {"name": "GitHub", "status": "connected"},
    {"name": "Okta", "status": "error"},
    {"name": "Splunk", "status": "disconnected"},
]
