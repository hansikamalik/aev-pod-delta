import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_JIRA_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _JIRA_ROOT not in sys.path:
    sys.path.insert(0, _JIRA_ROOT)

if "jira_connector" in sys.modules and not hasattr(sys.modules["jira_connector"], "FakeJiraAPIClient"):
    del sys.modules["jira_connector"]
