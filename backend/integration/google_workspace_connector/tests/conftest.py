import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_TESTS_DIR, "..", "src")
_AUTH_SRC_DIR = os.path.join(_TESTS_DIR, "..", "..", "google_workspace_auth", "src")

for path in (_SRC_DIR, _AUTH_SRC_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
