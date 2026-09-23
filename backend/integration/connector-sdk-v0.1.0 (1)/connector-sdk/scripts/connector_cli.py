#!/usr/bin/env python3
"""Integration Lead's connector CLI.

Loads any connector, runs it, and reports contract compliance without
needing to open pytest or read code. Built for two moments:

  1. Day-to-day review: is this connector even instantiable, does health
     check work, does a dry sync produce a sane SyncResult?
  2. Day 6 integration: run every registered connector back-to-back
     against the platform double and get one pass/fail report.

Usage
-----
List what's registered::

    python scripts/connector_cli.py list

Check one connector (imports it, validates config/credentials, runs
check_health + sync, prints a report)::

    python scripts/connector_cli.py check azure

Run the full contract test suite for one or all connectors::

    python scripts/connector_cli.py verify azure
    python scripts/connector_cli.py verify --all

Run every registered connector's sync() and print a combined report,
for Day 6 integration::

    python scripts/connector_cli.py integrate
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# --------------------------------------------------------------------------
# Registry — the single place that knows every connector in play.
#
# Add one entry per workstream as it lands. `factory` must return a fully
# constructed, ready-to-run Connector instance (using test doubles/mocks
# during Week 1, real clients once Day 6 wiring starts).
# --------------------------------------------------------------------------


@dataclass
class ConnectorEntry:
    key: str
    module: str          # dotted import path, e.g. "sample_connector"
    factory: str          # callable name inside that module, e.g. "build_for_cli"
    owner: str
    test_path: str        # path (relative to repo root) to its contract tests


REGISTRY: dict[str, ConnectorEntry] = {
    "sample": ConnectorEntry(
        key="sample",
        module="sample_connector.cli_factory",
        factory="build",
        owner="Harshal (reference)",
        test_path="tests/test_sample_connector.py",
    ),
    # "azure":  ConnectorEntry("azure",  "azure_connector.cli_factory",  "build", "Bhavesh/Subramani/Ashwin", "connectors/azure/tests"),
    # "splunk": ConnectorEntry("splunk", "splunk_connector.cli_factory", "build", "Ayyappatadi",              "connectors/splunk/tests"),
    # "fake":   ConnectorEntry("fake",   "connector_sdk.testing",         "FakeConnector",                     "Abhiram (infra double)", "tests/test_connector_base.py"),
}


def _load_connector(entry: ConnectorEntry):
    mod = importlib.import_module(entry.module)
    factory = getattr(mod, entry.factory)
    instance = factory() if callable(factory) else factory
    return instance


async def _run_sync(connector) -> "object":
    result = connector.sync()
    if inspect.isawaitable(result):
        return await result
    return result


def cmd_list(_args: argparse.Namespace) -> int:
    if not REGISTRY:
        print("No connectors registered yet. Add entries to REGISTRY in this file.")
        return 0
    print(f"{'key':<10} {'owner':<28} module")
    print("-" * 70)
    for entry in REGISTRY.values():
        print(f"{entry.key:<10} {entry.owner:<28} {entry.module}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    entry = REGISTRY.get(args.name)
    if entry is None:
        print(f"Unknown connector {args.name!r}. Run 'list' to see registered connectors.")
        return 1

    print(f"== {entry.key} ({entry.owner}) ==")
    try:
        connector = _load_connector(entry)
    except Exception as exc:
        print(f"  [FAIL] could not construct connector: {exc}")
        return 1

    print(f"  name: {connector.name}")

    try:
        connector.validate_configuration()
        print("  [ok] config + credentials match declared schemas")
    except Exception as exc:
        print(f"  [FAIL] configuration invalid: {exc}")
        return 1

    try:
        healthy = connector.check_health()
        print(f"  [{'ok' if healthy else 'WARN'}] check_health() -> {healthy}")
    except Exception as exc:
        print(f"  [FAIL] check_health() raised: {exc}")
        return 1

    try:
        result = asyncio.run(_run_sync(connector))
    except Exception as exc:
        print(f"  [FAIL] sync() raised (it must never raise): {exc}")
        return 1

    status_ok = str(result.status) in {"success", "partial", "failed"}
    print(f"  [{'ok' if status_ok else 'FAIL'}] sync -> status={result.status} "
          f"discovered={result.assets_discovered} pushed={result.assets_pushed} "
          f"errors={len(result.errors)}")
    for err in result.errors:
        print(f"      - {err.get('error_type')}: {err.get('message')}")

    return 0 if status_ok else 1


def cmd_verify(args: argparse.Namespace) -> int:
    if args.all:
        paths = [e.test_path for e in REGISTRY.values()]
    else:
        entry = REGISTRY.get(args.name)
        if entry is None:
            print(f"Unknown connector {args.name!r}.")
            return 1
        paths = [entry.test_path]

    cmd = [sys.executable, "-m", "pytest", "-v", *paths]
    print(f"$ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=REPO_ROOT)


def cmd_integrate(_args: argparse.Namespace) -> int:
    """Day 6: run every registered connector's sync() and report together."""
    if not REGISTRY:
        print("Nothing registered yet — add connectors to REGISTRY as they land.")
        return 1

    overall_ok = True
    print(f"{'connector':<10} {'status':<10} {'discovered':<11} {'pushed':<8} errors")
    print("-" * 60)
    for entry in REGISTRY.values():
        try:
            connector = _load_connector(entry)
            result = asyncio.run(_run_sync(connector))
            ok = str(result.status) != "failed"
            overall_ok = overall_ok and ok
            print(f"{entry.key:<10} {str(result.status):<10} "
                  f"{result.assets_discovered:<11} {result.assets_pushed:<8} "
                  f"{len(result.errors)}")
        except Exception as exc:
            overall_ok = False
            print(f"{entry.key:<10} {'CRASH':<10} {'-':<11} {'-':<8} {exc}")

    print("-" * 60)
    print("INTEGRATION " + ("PASSED" if overall_ok else "FAILED"))
    return 0 if overall_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List registered connectors").set_defaults(func=cmd_list)

    p_check = sub.add_parser("check", help="Instantiate, health-check, and sync one connector")
    p_check.add_argument("name")
    p_check.set_defaults(func=cmd_check)

    p_verify = sub.add_parser("verify", help="Run the pytest contract suite for one or all connectors")
    p_verify.add_argument("name", nargs="?", default=None)
    p_verify.add_argument("--all", action="store_true")
    p_verify.set_defaults(func=cmd_verify)

    sub.add_parser("integrate", help="Run every registered connector's sync() together (Day 6)").set_defaults(func=cmd_integrate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
