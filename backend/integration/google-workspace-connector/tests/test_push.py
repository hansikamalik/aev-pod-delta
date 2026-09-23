from unittest.mock import MagicMock, patch

import requests

from google_workspace_connector.base import Asset
from google_workspace_connector.push import BetaPlatformPusher

SAMPLE_ASSET = Asset(
    external_id="user-123",
    source="google_workspace",
    asset_type="user",
    name="jane@customer.com",
)


@patch("google_workspace_connector.push.requests.post")
def test_push_success(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    pusher = BetaPlatformPusher(api_token="fake-token")
    result = pusher.push("google_workspace", [SAMPLE_ASSET])

    assert result.success is True
    assert result.assets_count == 1
    assert result.errors == []
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer fake-token"


@patch("google_workspace_connector.push.requests.post")
def test_push_records_error_on_request_exception(mock_post):
    mock_post.side_effect = requests.ConnectionError("connection refused")

    pusher = BetaPlatformPusher(api_token="fake-token")
    result = pusher.push("google_workspace", [SAMPLE_ASSET])

    assert result.success is False
    assert "connection refused" in result.errors[0]


@patch("google_workspace_connector.push.requests.post")
def test_push_records_error_on_http_error_status(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_post.return_value = mock_response

    pusher = BetaPlatformPusher(api_token="fake-token")
    result = pusher.push("google_workspace", [SAMPLE_ASSET])

    assert result.success is False
    assert "500 Server Error" in result.errors[0]


@patch("google_workspace_connector.push.requests.post")
def test_push_with_empty_assets(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    pusher = BetaPlatformPusher(api_token="fake-token")
    result = pusher.push("google_workspace", [])

    assert result.assets_count == 0
    assert result.success is True
