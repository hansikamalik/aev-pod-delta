"""
Mock Splunk — HEC-style event endpoint and fixture events for Ayyappatadi's
connector tests.
"""
from __future__ import annotations

import json
import random
import string
from pathlib import Path
from typing import Any, Dict, List, Optional

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def mock_splunk_events() -> List[Dict[str, Any]]:
    with open(FIXTURE_DIR / "splunk_events.json", encoding="utf-8") as fh:
        return json.load(fh)


class MockSplunkHEC:
    """
    In-memory Splunk HTTP Event Collector.

    Usage in tests:
        hec = MockSplunkHEC(valid_token="team-token")
        client = SplunkConnector(hec_endpoint=hec.url)
        ...
        assert hec.received_count() == expected
    """

    def __init__(self, valid_token: str = "team-splunk-token") -> None:
        self.valid_token = valid_token
        self.received: List[Dict[str, Any]] = []
        self.fail_next_n: int = 0  # simulate transient 5xx responses

    # -- HEC wire behaviour ---------------------------------------------------
    def send_event(
        self, token: Optional[str], event: Dict[str, Any]
    ) -> tuple[int, Dict[str, Any]]:
        if token != self.valid_token:
            return 401, {"text": "Invalid authorization token"}
        if self.fail_next_n > 0:
            self.fail_next_n -= 1
            return 503, {"text": "Service Unavailable"}
        self.received.append(event)
        code = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return 200, {"text": "Success", "code": 0, "ackID": len(self.received), "data": code}

    # -- assertions helpers -----------------------------------------------------
    def received_count(self) -> int:
        return len(self.received)

    def reset(self) -> None:
        self.received.clear()
        self.fail_next_n = 0
