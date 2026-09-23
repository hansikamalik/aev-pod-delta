"""Asset validation helpers used by contract tests and module tests.

Aligned to contract_v2 §5-§9 (Asset), §6 (stable identity), §7 (source),
§8 (AssetType), §16 (no secrets in raw), §19 (no secrets in errors).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

from jsonschema import Draft202012Validator

from qa.contracts import ASSET_TYPES

SCHEMA_PATH = Path(__file__).parent / "schemas" / "asset.schema.json"

# ISO-8601 with timezone (contract requires a discovery timestamp)
_ISO_TS = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

# §16/§19: secrets must never leak into raw payloads or error messages
_SECRET_KEY_HINTS = re.compile(
    r"(client_secret|secret|password|passwd|api[-_]?key|access[-_]?token|"
    r"private[-_]?key|authorization)", re.IGNORECASE,
)


def load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _payload_of(asset: Any) -> Any:
    if is_dataclass(asset) and not isinstance(asset, dict):
        return asdict(asset)
    return asset


def validate_asset(asset: Any) -> List[str]:
    """Validate one asset against the SDK contract; [] == valid."""
    payload = _payload_of(asset)

    if not isinstance(payload, dict):
        return [f"asset is not a dict/dataclass, got {type(asset).__name__}"]

    errors = sorted(
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(load_schema()).iter_errors(payload)
    )

    # §8: type must be an SDK-defined AssetType (schema covers it, but be loud)
    if payload.get("type") not in ASSET_TYPES:
        errors.append(f"type: {payload.get('type')!r} is not a SDK AssetType")

    # §5: discoveredAt must be a real timestamp
    ts = payload.get("discoveredAt")
    if ts is not None and not _ISO_TS.match(str(ts)):
        errors.append(f"discoveredAt: must be ISO-8601 with timezone, got {ts!r}")

    # §6: no random/generated-looking UUID ids for source resources
    asset_id = str(payload.get("id", ""))
    if asset_id.endswith(("-0000-0000-0000-000000000000",)):  # obvious stubs
        errors.append("id: looks generated, must be a stable source identifier")

    # §16/§19: secrets never in raw
    raw = payload.get("raw")
    if isinstance(raw, dict):
        for key in raw:
            if _SECRET_KEY_HINTS.search(str(key)):
                errors.append(f"raw: suspected secret field {key!r} — must never be stored")

    # §5: tags are key/value string metadata when present
    tags = payload.get("tags")
    if isinstance(tags, dict):
        for k, v in tags.items():
            if not isinstance(k, str) or not isinstance(v, str):
                errors.append(f"tags: keys and values must be strings ({k!r}={v!r})")

    return errors


def validate_assets(assets: Iterable[Any]) -> List[str]:
    """Validate a batch of assets; returns all violations found."""
    errors: List[str] = []
    for i, asset in enumerate(assets):
        errors.extend(f"[{i}]{e}" for e in validate_asset(asset))
    return errors
