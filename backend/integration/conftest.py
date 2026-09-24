# backend/integration/conftest.py
import sys
from pathlib import Path

INTEGRATION_ROOT = Path(__file__).resolve().parent

# Automatically append every sub-directory to sys.path
for path in INTEGRATION_ROOT.rglob("*"):
    if path.is_dir() and path.name in ("src", "aev_connectors", "github_connector", "connector_sdk"):
        sys.path.insert(0, str(path))
    elif path.is_dir() and (path / "src").exists():
        sys.path.insert(0, str(path / "src"))
    elif path.is_dir() and (path / "tests").exists():
        sys.path.insert(0, str(path))
