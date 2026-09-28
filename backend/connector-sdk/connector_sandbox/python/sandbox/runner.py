from __future__ import annotations

import argparse
from typing import Sequence

from connector_sdk import SyncStatus
from connectors.reference.connector import ReferenceConnector


def run_connector(connector, scenario: str = "success"):
    print(f"Running connector: {connector.name}")
    print(f"Scenario: {scenario}")

    result = connector.sync()

    print(f"Status: {result.status}")
    print(f"Assets discovered: {result.assets_discovered}")
    print(f"Assets pushed: {result.assets_pushed}")

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  - {error}")

    return result


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns 0 on a SUCCESS sync, 1 otherwise."""
    parser = argparse.ArgumentParser(description="Run a connector against the mock server")
    parser.add_argument("--connector", choices=["reference"], default="reference")
    parser.add_argument("--scenario", default="success")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args(argv)

    connector = ReferenceConnector(
        base_url=args.base_url,
        api_key="sandbox-test-key",
        # The mock server picks its behaviour from ?scenario=<name>.
        extra_params={"scenario": args.scenario},
    )
    result = run_connector(connector, scenario=args.scenario)
    return 0 if result.status == SyncStatus.SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
