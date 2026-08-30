import pytest
from unittest.mock import patch, MagicMock

from pipeline.utils.baidu_auth import get_baidu_access_token


@pytest.mark.unit
class TestBaiduAuth:
    @patch("pipeline.utils.baidu_auth.requests.post")
    def test_get_access_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "test-token-123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token = get_baidu_access_token("api_key", "secret_key")
        assert token == "test-token-123"

    @patch("pipeline.utils.baidu_auth.requests.post")
    def test_get_access_token_missing_token_raises(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "invalid_client"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Failed to get Baidu access token"):
            get_baidu_access_token("bad_key", "bad_secret")

    @patch("pipeline.utils.baidu_auth.requests.post")
    def test_get_access_token_http_error_propagates(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.HTTPError("403 Forbidden")

        with pytest.raises(req.exceptions.HTTPError):
            get_baidu_access_token("key", "secret")
