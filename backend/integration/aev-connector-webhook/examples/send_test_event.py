"""Send one correctly signed inbound event to a locally running connector.

    python examples/send_test_event.py
"""

from __future__ import annotations

import json
import os

import httpx

from aev_connectors.webhook.signing import build_signature_header

BASE_URL = os.getenv("AEV_BASE_URL", "http://localhost:8000")
SECRET = os.getenv("WEBHOOK_SIGNING_SECRET", "dev-secret-change-me")

PAYLOAD = {
    "event_type": "asset.created",
    "assets": [{"id": "i-0abc", "hostname": "web-01", "type": "ec2", "ip": "10.0.0.4"}],
    "findings": [
        {"id": "f-1", "asset_id": "i-0abc", "severity": "high", "title": "Open port 22"}
    ],
}


def main() -> None:
    body = json.dumps(PAYLOAD).encode()
    signature, timestamp = build_signature_header(SECRET, body)
    headers = {
        "Content-Type": "application/json",
        "X-AEV-Signature": signature,
        "X-AEV-Timestamp": str(timestamp),
    }

    inbound = httpx.post(f"{BASE_URL}/connectors/webhook/events", content=body, headers=headers)
    print("inbound:", inbound.status_code, inbound.text)

    synced = httpx.post(f"{BASE_URL}/connectors/webhook/sync")
    print("sync:   ", synced.status_code, synced.text)


if __name__ == "__main__":
    main()
