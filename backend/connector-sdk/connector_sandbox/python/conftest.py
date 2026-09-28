"""
Shared fixtures for python-sandbox-v2's own test suite.

Two ways of exercising the mock server, used for different purposes:

- `api_client`: FastAPI's TestClient, wraps the ASGI app in-process.
  No socket, no thread, no timing issues. Use this for testing the
  mock server's *endpoints* directly (status codes, payload shapes).

- `live_server`: a real uvicorn server on a real localhost port, run in
  a background thread. Use this for testing `ReferenceConnector`,
  because it makes real `httpx.get(url)` calls against a URL string --
  it can't be pointed at an in-process ASGI app the way TestClient can.
"""
from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from mock_server.server import app


@pytest.fixture
def api_client() -> TestClient:
    """In-process client for testing mock server endpoints directly."""
    return TestClient(app)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server():
    """Runs the actual mock_server FastAPI app on a real localhost port.

    Yields the base URL. Server shuts down automatically after the test.
    Needed for connector-level tests, since ReferenceConnector talks to
    a URL string over a real socket rather than an in-process app.
    """
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"

    # Wait for the server to actually be ready instead of guessing with
    # a fixed sleep -- avoids flaky tests on slower machines/CI.
    deadline = time.monotonic() + 5.0
    last_error = None
    while time.monotonic() < deadline:
        try:
            httpx.get(f"{base_url}/health", timeout=0.5)
            break
        except httpx.HTTPError as exc:
            last_error = exc
            time.sleep(0.05)
    else:
        raise RuntimeError(f"live_server did not become ready in time: {last_error}")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5.0)