import pytest
from unittest.mock import patch
from client import SplunkClient, SplunkAPIError


def test_splunk_ping_success():
    client = SplunkClient(host="splunk.local", bearer_token="valid_token")
    
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        assert client.ping() is True


def test_splunk_create_search_job_failure():
    client = SplunkClient(host="splunk.local", bearer_token="valid_token")
    
    with patch.object(client.session, "post") as mock_post:
        mock_post.side_effect = Exception("Connection Timeout")
        with pytest.raises(SplunkAPIError):
            client.create_search_job("search index=_internal")
