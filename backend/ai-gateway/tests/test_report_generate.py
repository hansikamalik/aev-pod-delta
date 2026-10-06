from app.tools import dispatch_tool


def test_report_generate():
    response = dispatch_tool(
        "report_generate",
        {
            "asset_id": "asset-001",
            "report_type": "security",
        },
        user_id="test-user",
        role="analyst",
    )

    assert response["ok"] is True
    assert response["result"]["tool"] == "report_generate"
    assert response["result"]["asset_id"] == "asset-001"
    assert response["result"]["report_type"] == "security"
    assert response["result"]["status"] == "generated"
    assert response["result"]["citations"]


def test_report_generate_default_type():
    response = dispatch_tool(
        "report_generate",
        {
            "asset_id": "asset-001",
        },
        user_id="test-user",
        role="analyst",
    )

    assert response["ok"] is True
    assert response["result"]["report_type"] == "security"


def test_report_generate_invalid_type():
    response = dispatch_tool(
        "report_generate",
        {
            "asset_id": "asset-001",
            "report_type": "invalid",
        },
        user_id="test-user",
        role="analyst",
    )

    assert response["ok"] is False


def test_viewer_cannot_generate_report():
    response = dispatch_tool(
        "report_generate",
        {
            "asset_id": "asset-001",
        },
        user_id="test-user",
        role="viewer",
    )

    assert response["ok"] is False


def test_report_generate_requires_asset():
    response = dispatch_tool(
        "report_generate",
        {},
        user_id="test-user",
        role="analyst",
    )

    assert response["ok"] is False
