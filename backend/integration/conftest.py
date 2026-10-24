# backend/integration/conftest.py
import sys
from pathlib import Path

INTEGRATION_ROOT = Path(__file__).resolve().parent
CANONICAL_SDK = INTEGRATION_ROOT.parent / "connector-sdk"

# Ensure the canonical connector SDK is always first in sys.path
if CANONICAL_SDK.exists():
    sys.path.insert(0, str(CANONICAL_SDK))

# Automatically append valid connector sub-directories to sys.path
for path in sorted(INTEGRATION_ROOT.glob("*")):
    if "connector-sdk-v0.1.0" in path.name:
        continue
    if path.is_dir() and (path / "src").exists():
        sys.path.insert(0, str(path / "src"))
    elif path.is_dir() and path.name in ("integration-service", "jira_connector"):
        sys.path.insert(0, str(path))
