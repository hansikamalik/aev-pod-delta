import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_TESTS_DIR, "..", "src")
_AUTH_SRC_DIR = os.path.join(_TESTS_DIR, "..", "..", "google_workspace_auth", "src")
_ENGINE_SRC_DIR = os.path.join(
    _TESTS_DIR,
    "..",
    "..",
    "enterprise_sync_engine_hardened",
)

for path in (_ENGINE_SRC_DIR, _AUTH_SRC_DIR, _SRC_DIR):
    path = os.path.abspath(path)
    if path not in sys.path:
        sys.path.insert(0, path)