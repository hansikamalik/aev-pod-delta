from datetime import datetime, timezone
from typing import Any, Dict
from sync_engine.models import Asset

SECRET_KEY_BLOCKLIST = {
    "bearer_token", "token", "authorization", "password", 
    "sec_token", "session_key", "session_id", "authtoken",
    "api_key", "secret", "private_key", "client_secret"
}


def sanitize_payload(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redacts sensitive security keys from incoming raw data."""
    clean_payload = {}
    for key, value in raw_data.items():
        if key.lower() in SECRET_KEY_BLOCKLIST:
            continue
        if isinstance(value, dict):
            clean_payload[key] = sanitize_payload(value)
        elif isinstance(value, list):
            clean_payload[key] = [
                sanitize_payload(item) if isinstance(item, dict) else item 
                for item in value
            ]
        else:
            clean_payload[key] = value
    return clean_payload


def normalize_event_to_asset(event: Dict[str, Any], connector_name: str) -> Asset:
    asset_id = str(event.get("_cd") or event.get("id") or event.get("uuid") or hash(str(event)))
    
    raw_time = event.get("_time") or event.get("timestamp") or event.get("created_at")
    discovered_at = datetime.now(timezone.utc)
    if raw_time:
        try:
            if isinstance(raw_time, (int, float)):
                discovered_at = datetime.fromtimestamp(raw_time, tz=timezone.utc)
            else:
                discovered_at = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
        except Exception:
            pass

    event_name = event.get("_raw") or event.get("name") or event.get("message") or f"{connector_name} Event {asset_id}"
    if len(str(event_name)) > 120:
        event_name = str(event_name)[:117] + "..."

    sanitized_raw = sanitize_payload(event)

    return Asset(
        id=asset_id,
        source=connector_name,
        type="detection",
        name=str(event_name),
        raw=sanitized_raw,
        discoveredAt=discovered_at,
        tags={
            "index": str(event.get("index", "default")),
            "host": str(event.get("host", "unknown"))
        }
    )
