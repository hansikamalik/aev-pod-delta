"""
Docker image entrypoint: runs SampleConnector end to end with no network
and no credentials, so `docker run <image>` proves the image works with
a single command. Exits 0 on SyncStatus.SUCCESS, 1 otherwise.
"""
from __future__ import annotations

import json
import sys

from connector_sdk import SampleConnector, SyncStatus


def main() -> int:
    connector = SampleConnector()
    result = connector.sync()

    print(json.dumps({
        "connector": result.connector,
        "status": result.status.value,
        "assets_discovered": result.assets_discovered,
        "assets_pushed": result.assets_pushed,
        "errors": result.errors,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
    }, indent=2))

    return 0 if result.status == SyncStatus.SUCCESS else 1


if __name__ == "__main__":
    sys.exit(main())
