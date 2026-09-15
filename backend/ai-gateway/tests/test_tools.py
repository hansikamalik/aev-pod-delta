import pytest

from app import tools


@pytest.fixture(autouse=True)
def clean_registry():
    """Give every test a clean registry so tests don't affect each other."""
    original = dict(tools._TOOL_REGISTRY)
    tools._TOOL_REGISTRY.clear()
    yield
    tools._TOOL_REGISTRY.clear()
    tools._TOOL_REGISTRY.update(original)


# ---------------------------------------------------------
# Registration
# ---------------------------------------------------------

def test_registered_tool_appears_in_registry():
    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {"score": 92}

    assert "risk_score_get" in tools.get_registered_tools()


def test_registering_same_tool_twice_raises():
    @tools.register_tool("risk_score_get")
    def first(user_id, asset_id):
        return {}

    with pytest.raises(tools.ToolError):
        @tools.register_tool("risk_score_get")
        def second(user_id, asset_id):
            return {}


def test_only_implemented_tools_are_advertised():
    """
    A tool with a schema but no implementation must not be sent to the
    model -- otherwise the model can request something undispatchable.
    """

    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {"score": 92}

    advertised = [s["name"] for s in tools.get_tool_schemas()]

    assert advertised == ["risk_score_get"]
    assert "asset_search" not in advertised


# ---------------------------------------------------------
# Dispatch
# ---------------------------------------------------------

def test_dispatch_runs_the_tool_and_returns_result():
    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {"asset_id": asset_id, "score": 92}

    response = tools.dispatch_tool(
        "risk_score_get",
        {"asset_id": "db-prod-01"},
        user_id="hansika",
        role="admin",
    )

    assert response["ok"] is True
    assert response["result"]["score"] == 92
    assert response["error"] is None


def test_dispatch_passes_user_id_to_the_tool():
    """RBAC depends on every tool knowing who is asking."""

    seen = {}

    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        seen["user_id"] = user_id
        return {}

    tools.dispatch_tool(
        "risk_score_get",
        {"asset_id": "db-prod-01"},
        user_id="hansika",
        role="admin",
    )

    assert seen["user_id"] == "hansika"


def test_unknown_tool_is_rejected_not_crashed():
    response = tools.dispatch_tool(
        "not_a_real_tool", {}, user_id="hansika", role="admin"
    )

    assert response["ok"] is False
    assert "Unknown" in response["error"]


def test_missing_required_argument_is_rejected():
    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {}

    response = tools.dispatch_tool(
        "risk_score_get", {}, user_id="hansika", role="admin"
    )

    assert response["ok"] is False
    assert "asset_id" in response["error"]


def test_unexpected_argument_is_rejected():
    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {}

    response = tools.dispatch_tool(
        "risk_score_get",
        {"asset_id": "db-prod-01", "sneaky": "value"},
        user_id="hansika",
        role="admin",
    )

    assert response["ok"] is False
    assert "sneaky" in response["error"]


def test_failing_tool_returns_error_instead_of_crashing():
    """
    A tool blowing up must not take down the whole request -- the model
    needs the chance to explain the failure to the user.
    """

    @tools.register_tool("risk_score_get")
    def broken(user_id, asset_id):
        raise RuntimeError("Beta service unreachable")

    response = tools.dispatch_tool(
        "risk_score_get",
        {"asset_id": "db-prod-01"},
        user_id="hansika",
        role="admin",
    )

    assert response["ok"] is False
    assert "Beta service unreachable" in response["error"]


def test_optional_arguments_can_be_omitted():
    @tools.register_tool("exposure_query")
    def fake_exposures(user_id, asset_id=None, severity=None):
        return {"count": 3}

    response = tools.dispatch_tool(
        "exposure_query", {}, user_id="hansika", role="admin"
    )

    assert response["ok"] is True
    assert response["result"]["count"] == 3


# ---------------------------------------------------------
# RBAC enforcement
# ---------------------------------------------------------

def test_role_without_permission_is_denied():
    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {"score": 92}

    response = tools.dispatch_tool(
        "risk_score_get",
        {"asset_id": "db-prod-01"},
        user_id="someone",
        role="viewer",  # viewer is not allowed risk_score_get
    )

    assert response["ok"] is False
    assert "not permitted" in response["error"]


def test_denied_role_never_runs_the_tool():
    """
    A permission denial must stop execution entirely -- the tool
    function itself should never run for a caller who isn't allowed.
    """

    called = {"ran": False}

    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        called["ran"] = True
        return {}

    tools.dispatch_tool(
        "risk_score_get",
        {"asset_id": "db-prod-01"},
        user_id="someone",
        role="viewer",
    )

    assert called["ran"] is False


def test_anonymous_role_is_denied_even_for_a_permitted_tool():
    @tools.register_tool("asset_search")
    def fake_search(user_id, query):
        return {"results": []}

    response = tools.dispatch_tool(
        "asset_search",
        {"query": "prod database"},
        user_id="anonymous",
        role="anonymous",
    )

    assert response["ok"] is False


def test_permission_denial_happens_before_argument_validation():
    """
    A caller without permission should not learn anything about the
    tool's expected arguments -- so an empty/invalid argument set from
    an unauthorized role should still fail with a permission error, not
    an argument error.
    """

    @tools.register_tool("risk_score_get")
    def fake_risk(user_id, asset_id):
        return {}

    response = tools.dispatch_tool(
        "risk_score_get",
        {},  # missing required asset_id -- but role gets checked first
        user_id="someone",
        role="viewer",
    )

    assert response["ok"] is False
    assert "not permitted" in response["error"]