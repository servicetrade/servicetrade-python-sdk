"""Comprehensive test suite for the ServiceTrade Python SDK."""

import base64
import json
import time
from unittest.mock import MagicMock

import pytest
import responses

from servicetrade import (
    FileAttachment,
    ServicetradeAPIError,
    ServicetradeAuthError,
    ServicetradeClient,
    ServicetradeResponse,
)

BASE_URL = "https://api.servicetrade.com"
API_PREFIX = "/api"


def create_mock_token(exp_offset: int = 3600) -> str:
    """Create a mock JWT token with configurable expiry."""
    header = (
        base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode())
        .decode()
        .rstrip("=")
    )
    payload = (
        base64.urlsafe_b64encode(
            json.dumps({"exp": int(time.time()) + exp_offset}).encode()
        )
        .decode()
        .rstrip("=")
    )
    signature = base64.urlsafe_b64encode(b"signature").decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


def mock_auth() -> str:
    """Register a mock auth endpoint and return the token."""
    token = create_mock_token()
    responses.add(
        responses.POST,
        f"{BASE_URL}/oauth2/token",
        json={"access_token": token},
        status=200,
    )
    return token


class TestModuleExports:
    """Test module exports and structure."""

    def test_exports_servicetrade_client(self):
        from servicetrade import ServicetradeClient

        assert ServicetradeClient is not None

    def test_exports_types(self):
        from servicetrade import (
            BearerToken,
            FileAttachment,
            Paginator,
            ServicetradeClientOptions,
            ServicetradeClientResponse,
            ServicetradeResponse,
        )

        assert BearerToken is not None
        assert FileAttachment is not None
        assert Paginator is not None
        assert ServicetradeClientOptions is not None
        assert ServicetradeClientResponse is not None
        assert ServicetradeResponse is not None

    def test_exports_exceptions(self):
        from servicetrade import (
            ServicetradeAPIError,
            ServicetradeAuthError,
            ServicetradeError,
        )

        assert ServicetradeError is not None
        assert ServicetradeAuthError is not None
        assert ServicetradeAPIError is not None


class TestConstructor:
    """Test ServicetradeClient constructor."""

    def test_requires_credentials(self):
        with pytest.raises(ServicetradeAuthError) as exc_info:
            ServicetradeClient()
        assert "required" in str(exc_info.value)

    def test_accepts_client_credentials(self):
        client = ServicetradeClient(client_id="id", client_secret="secret")
        assert client is not None

    def test_accepts_refresh_token(self):
        client = ServicetradeClient(refresh_token="refresh_token")
        assert client is not None

    def test_accepts_bearer_token(self):
        token = create_mock_token()
        client = ServicetradeClient(token=token)
        assert client is not None

    def test_custom_base_url(self):
        client = ServicetradeClient(
            base_url="https://staging.servicetrade.com",
            client_id="id",
            client_secret="secret",
        )
        assert client._options.base_url == "https://staging.servicetrade.com"

    def test_custom_user_agent(self):
        client = ServicetradeClient(
            user_agent="Custom Agent/1.0",
            client_id="id",
            client_secret="secret",
        )
        assert client._options.user_agent == "Custom Agent/1.0"

    def test_rejects_username_password(self):
        """Password grant is not supported — only client_credentials, refresh_token, or token."""
        with pytest.raises(ServicetradeAuthError):
            ServicetradeClient(username="user", password="pass")


class TestLogin:
    """Test login functionality."""

    @responses.activate
    def test_login_with_client_credentials(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        result = client.login()

        assert result == token

    @responses.activate
    def test_login_with_refresh_token(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token, "refresh_token": "new_refresh"},
            status=200,
        )

        client = ServicetradeClient(refresh_token="old_refresh")
        result = client.login()

        assert result == token
        assert client._credentials.refresh_token == "new_refresh"

    @responses.activate
    def test_login_calls_on_set_auth_callback(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        callback = MagicMock()
        client = ServicetradeClient(
            client_id="id",
            client_secret="secret",
            on_set_auth=callback,
        )
        client.login()

        callback.assert_called_once_with(token)

    @responses.activate
    def test_login_failure(self):
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"error": "invalid_grant"},
            status=401,
        )

        client = ServicetradeClient(client_id="id", client_secret="wrong")

        with pytest.raises(ServicetradeAuthError) as exc_info:
            client.login()

        assert exc_info.value.status_code == 401


class TestLogout:
    """Test logout functionality."""

    @responses.activate
    def test_logout_clears_token(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token, "refresh_token": "refresh"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/revoke",
            status=200,
        )

        client = ServicetradeClient(refresh_token="refresh")
        client.login()
        client.logout()

        assert client._token is None

    @responses.activate
    def test_logout_calls_callback(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/revoke",
            status=200,
        )

        callback = MagicMock()
        client = ServicetradeClient(
            refresh_token="refresh",
            on_unset_auth=callback,
        )
        client.login()
        client.logout()

        callback.assert_called_once()

    @responses.activate
    def test_logout_suppresses_revoke_errors(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token, "refresh_token": "refresh"},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/revoke",
            status=500,
        )

        client = ServicetradeClient(refresh_token="refresh")
        client.login()
        # Should not raise
        client.logout()


class TestHTTPMethods:
    """Test HTTP request methods."""

    @responses.activate
    def test_get_request(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/123",
            json={"data": {"id": 123, "name": "Test Job"}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.get("/job/123")

        assert result == {"id": 123, "name": "Test Job"}

    @responses.activate
    def test_post_request(self):
        mock_auth()
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/jobitem",
            json={"data": {"id": 456}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.post("/jobitem", {"name": "New Item"})

        assert result == {"id": 456}

    @responses.activate
    def test_put_request(self):
        mock_auth()
        responses.add(
            responses.PUT,
            f"{BASE_URL}{API_PREFIX}/jobitem/456",
            json={"data": {"id": 456, "updated": True}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.put("/jobitem/456", {"name": "Updated Item"})

        assert result == {"id": 456, "updated": True}

    @responses.activate
    def test_delete_request(self):
        mock_auth()
        responses.add(
            responses.DELETE,
            f"{BASE_URL}{API_PREFIX}/job/123",
            body="",
            status=204,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.delete("/job/123")

        assert result is None

    @responses.activate
    def test_returns_none_for_empty_data(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/empty",
            body="",
            status=204,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.get("/empty")

        assert result is None

    @responses.activate
    def test_returns_list_response(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/items",
            json=[{"id": 1}, {"id": 2}, {"id": 3}],
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.get("/items")

        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


class TestQueryParameters:
    """Test query parameter support."""

    @responses.activate
    def test_get_with_params(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": [{"id": 1}]},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        client.get("/job", params={"status": "open", "page": 0})

        # Verify query params were sent
        assert "status=open" in responses.calls[-1].request.url
        assert "page=0" in responses.calls[-1].request.url

    @responses.activate
    def test_post_with_params(self):
        mock_auth()
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/job",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        client.post("/job", {"name": "Test"}, params={"draft": "true"})

        assert "draft=true" in responses.calls[-1].request.url

    @responses.activate
    def test_put_with_params(self):
        mock_auth()
        responses.add(
            responses.PUT,
            f"{BASE_URL}{API_PREFIX}/job/1",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        client.put("/job/1", {"name": "Test"}, params={"notify": "true"})

        assert "notify=true" in responses.calls[-1].request.url

    @responses.activate
    def test_delete_with_params(self):
        mock_auth()
        responses.add(
            responses.DELETE,
            f"{BASE_URL}{API_PREFIX}/job/1",
            body="",
            status=204,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        client.delete("/job/1", params={"force": "true"})

        assert "force=true" in responses.calls[-1].request.url


class TestLazyAuth:
    """Test lazy authentication (auto-login on first request)."""

    @responses.activate
    def test_get_without_login(self):
        """Should automatically login on first API call."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/1",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        # No login() call — should auto-authenticate
        result = client.get("/job/1")

        assert result == {"id": 1}
        assert client._token == token

    @responses.activate
    def test_token_only_no_lazy_auth(self):
        """With only a pre-existing token and no credentials, should use the token directly."""
        token = create_mock_token()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/1",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(token=token)
        result = client.get("/job/1")

        assert result == {"id": 1}


class TestDeleteReturnsNone:
    """Test that delete() returns None."""

    @responses.activate
    def test_delete_returns_none(self):
        mock_auth()
        responses.add(
            responses.DELETE,
            f"{BASE_URL}{API_PREFIX}/job/123",
            json={"data": {"deleted": True}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.delete("/job/123")

        assert result is None


class TestGetAuthToken:
    """Test get_auth_token() accessor."""

    def test_returns_none_before_login(self):
        client = ServicetradeClient(client_id="id", client_secret="secret")
        assert client.get_auth_token() is None

    @responses.activate
    def test_returns_token_after_login(self):
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        assert client.get_auth_token() == token


class TestGetLastResponse:
    """Test get_last_response()."""

    @responses.activate
    def test_returns_none_before_request(self):
        client = ServicetradeClient(client_id="id", client_secret="secret")
        assert client.get_last_response() is None

    @responses.activate
    def test_returns_response_after_request(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/1",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        client.get("/job/1")

        last = client.get_last_response()
        assert last is not None
        assert isinstance(last, ServicetradeResponse)
        assert last.status_code == 200
        assert last.is_success()
        assert last.body == {"data": {"id": 1}}
        assert last.decoded_body() == {"data": {"id": 1}}

    @responses.activate
    def test_stores_error_response(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/bad",
            json={"error": "not found"},
            status=404,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        with pytest.raises(ServicetradeAPIError):
            client.get("/bad")

        last = client.get_last_response()
        assert last is not None
        assert last.status_code == 404
        assert not last.is_success()


class TestReentrancyGuard:
    """Test reentrancy guard on login."""

    @responses.activate
    def test_prevents_recursive_login(self):
        """on_set_auth callback calling login() should raise."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        def bad_callback(t: str) -> None:
            client.login()  # This should trigger reentrancy guard

        client = ServicetradeClient(
            client_id="id",
            client_secret="secret",
            on_set_auth=bad_callback,
        )

        with pytest.raises(ServicetradeAuthError, match="reentrancy"):
            client.login()


class TestURLNormalization:
    """Test URL normalization."""

    def test_strips_trailing_slash_from_base_url(self):
        client = ServicetradeClient(
            base_url="https://api.servicetrade.com/",
            client_id="id",
            client_secret="secret",
        )
        assert client._options.base_url == "https://api.servicetrade.com"

    def test_normalizes_api_prefix(self):
        client = ServicetradeClient(
            api_prefix="api",
            client_id="id",
            client_secret="secret",
        )
        assert client._options.api_prefix == "/api"

    @responses.activate
    def test_normalizes_path_in_request(self):
        """Paths without leading slash should still work."""
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/1",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.get("job/1")

        assert result == {"id": 1}

    @responses.activate
    def test_no_double_slash(self):
        """Trailing slash on base_url + leading slash on path should not cause double slashes."""
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/1",
            json={"data": {"id": 1}},
            status=200,
        )

        client = ServicetradeClient(
            base_url="https://api.servicetrade.com/",
            client_id="id",
            client_secret="secret",
        )
        client.login()
        result = client.get("/job/1")

        assert result == {"id": 1}
        # Verify no double slashes in the URL (excluding https://)
        request_url = responses.calls[-1].request.url
        assert "//" not in request_url.replace("https://", "")


class TestAutoRefresh:
    """Test automatic token refresh."""

    @responses.activate
    def test_refreshes_on_401(self):
        old_token = create_mock_token()
        new_token = create_mock_token()

        # Initial login
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": old_token},
            status=200,
        )
        # First request returns 401
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/123",
            status=401,
        )
        # Refresh token
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": new_token},
            status=200,
        )
        # Retry succeeds
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/123",
            json={"data": {"id": 123}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        result = client.get("/job/123")

        assert result == {"id": 123}
        assert client._token == new_token

    @responses.activate
    def test_refreshes_stale_token_before_request(self):
        expired_token = create_mock_token(exp_offset=-100)
        new_token = create_mock_token()

        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": new_token},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/123",
            json={"data": {"id": 123}},
            status=200,
        )

        client = ServicetradeClient(
            token=expired_token, client_id="id", client_secret="secret"
        )
        result = client.get("/job/123")

        assert result == {"id": 123}
        assert client._token == new_token


class TestFileAttachment:
    """Test file attachment functionality."""

    @responses.activate
    def test_attach_file(self):
        mock_auth()
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/attachment",
            json={"data": {"id": 789, "filename": "test.txt"}},
            status=200,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        file = FileAttachment(
            value=b"test content",
            filename="test.txt",
            content_type="text/plain",
        )
        result = client.attach({"description": "Test file"}, file)

        assert result == {"id": 789, "filename": "test.txt"}


class TestCustomHeaders:
    """Test custom header functionality."""

    @responses.activate
    def test_set_custom_header(self):
        mock_auth()

        def request_callback(request):
            assert request.headers.get("X-Custom-Header") == "custom-value"
            return (200, {}, json.dumps({"data": {"success": True}}))

        responses.add_callback(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/test",
            callback=request_callback,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()
        client.set_custom_header("X-Custom-Header", "custom-value")
        result = client.get("/test")

        assert result == {"success": True}

    @responses.activate
    def test_custom_user_agent(self):
        token = create_mock_token()

        def auth_callback(request):
            assert "Custom/1.0" in request.headers.get("User-Agent", "")
            return (200, {}, json.dumps({"access_token": token}))

        responses.add_callback(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            callback=auth_callback,
        )

        client = ServicetradeClient(
            client_id="id",
            client_secret="secret",
            user_agent="Custom/1.0",
        )
        client.login()


class TestErrorHandling:
    """Test error handling."""

    @responses.activate
    def test_api_error_includes_status_code(self):
        mock_auth()
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/notfound",
            json={"error": "Not found"},
            status=404,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        with pytest.raises(ServicetradeAPIError) as exc_info:
            client.get("/notfound")

        assert exc_info.value.status_code == 404

    @responses.activate
    def test_api_error_includes_response_data(self):
        mock_auth()
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/invalid",
            json={"error": "Validation failed", "details": ["field required"]},
            status=400,
        )

        client = ServicetradeClient(client_id="id", client_secret="secret")
        client.login()

        with pytest.raises(ServicetradeAPIError) as exc_info:
            client.post("/invalid", {})

        assert exc_info.value.response_data is not None
        assert exc_info.value.response_data.get("error") == "Validation failed"


class TestEnhancedExceptions:
    """Test structured error parsing in ServicetradeAPIError."""

    def test_parses_error_messages(self):
        response_data = {
            "messages": {
                "error": ["Something went wrong", "Another error"]
            }
        }
        err = ServicetradeAPIError("fail", status_code=400, response_data=response_data)
        assert err.error_messages == ["Something went wrong", "Another error"]
        assert "Something went wrong" in err.message

    def test_parses_validation_messages(self):
        response_data = {
            "messages": {
                "validation": ["Field X is required", "Field Y is too long"]
            }
        }
        err = ServicetradeAPIError("fail", status_code=422, response_data=response_data)
        assert err.validation == ["Field X is required", "Field Y is too long"]
        assert "Field X is required" in err.message

    def test_parses_both_error_and_validation(self):
        response_data = {
            "messages": {
                "error": ["General failure"],
                "validation": ["Bad field"],
            }
        }
        err = ServicetradeAPIError("fail", status_code=400, response_data=response_data)
        assert err.error_messages == ["General failure"]
        assert err.validation == ["Bad field"]

    def test_handles_missing_messages(self):
        err = ServicetradeAPIError("fail", status_code=500, response_data={"other": "data"})
        assert err.error_messages == []
        assert err.validation == []
        assert err.message == "fail"

    def test_handles_none_response_data(self):
        err = ServicetradeAPIError("fail", status_code=500)
        assert err.error_messages == []
        assert err.validation == []

    def test_handles_string_error(self):
        response_data = {"messages": {"error": "single error string"}}
        err = ServicetradeAPIError("fail", status_code=400, response_data=response_data)
        assert err.error_messages == ["single error string"]
