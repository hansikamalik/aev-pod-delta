import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_INTEG_DIR = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
_SDK_SRC = os.path.join(_INTEG_DIR, "connector-sdk-v0.1.0 (1)", "connector-sdk", "src")

for p in (_TESTS_DIR, _INTEG_DIR, _SDK_SRC):
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    import connector_sdk as sdk
    import connector_sdk.connector
    import connector_sdk.models
    sys.modules.setdefault("sdk", sdk)
    sys.modules.setdefault("sdk.connector", connector_sdk.connector)
    sys.modules.setdefault("sdk.models", connector_sdk.models)
except ImportError:
    pass
