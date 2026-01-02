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
)

BASE_URL = "https://api.servicetrade.com"
API_PREFIX = "/api"


def create_mock_token(exp_offset: int = 3600) -> str:
    """Create a mock JWT token with configurable expiry.

    Args:
        exp_offset: Seconds from now until expiry.

    Returns:
        A mock JWT token string.
    """
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


class TestModuleExports:
    """Test module exports and structure."""

    def test_exports_servicetrade_client(self):
        """Should export ServicetradeClient class."""
        from servicetrade import ServicetradeClient

        assert ServicetradeClient is not None

    def test_exports_types(self):
        """Should export type definitions."""
        from servicetrade import (
            BearerToken,
            FileAttachment,
            ServicetradeClientOptions,
            ServicetradeClientResponse,
        )

        assert BearerToken is not None
        assert FileAttachment is not None
        assert ServicetradeClientOptions is not None
        assert ServicetradeClientResponse is not None

    def test_exports_exceptions(self):
        """Should export exception classes."""
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
        """Should raise error if no credentials provided."""
        with pytest.raises(ServicetradeAuthError) as exc_info:
            ServicetradeClient()
        assert "Username and password or clientId and clientSecret are required" in str(
            exc_info.value
        )

    def test_accepts_username_password(self):
        """Should accept username and password credentials."""
        client = ServicetradeClient(username="user", password="pass")
        assert client is not None

    def test_accepts_client_credentials(self):
        """Should accept client_id and client_secret credentials."""
        client = ServicetradeClient(client_id="id", client_secret="secret")
        assert client is not None

    def test_accepts_refresh_token(self):
        """Should accept refresh token."""
        client = ServicetradeClient(refresh_token="refresh_token")
        assert client is not None

    def test_accepts_bearer_token(self):
        """Should accept pre-existing bearer token."""
        token = create_mock_token()
        client = ServicetradeClient(token=token)
        assert client is not None

    def test_custom_base_url(self):
        """Should accept custom base URL."""
        client = ServicetradeClient(
            base_url="https://staging.servicetrade.com",
            username="user",
            password="pass",
        )
        assert client._options.base_url == "https://staging.servicetrade.com"

    def test_custom_user_agent(self):
        """Should accept custom user agent."""
        client = ServicetradeClient(
            user_agent="Custom Agent/1.0",
            username="user",
            password="pass",
        )
        assert client._options.user_agent == "Custom Agent/1.0"


class TestLogin:
    """Test login functionality."""

    @responses.activate
    def test_login_with_password(self):
        """Should authenticate with username/password."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
        result = client.login()

        assert result == token
        assert client._token == token

    @responses.activate
    def test_login_with_client_credentials(self):
        """Should authenticate with client credentials."""
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
        """Should authenticate with refresh token."""
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
        """Should call on_set_auth callback on successful login."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        callback = MagicMock()
        client = ServicetradeClient(
            username="user",
            password="pass",
            on_set_auth=callback,
        )
        client.login()

        callback.assert_called_once_with(token)

    @responses.activate
    def test_login_failure(self):
        """Should raise error on authentication failure."""
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"error": "invalid_grant"},
            status=401,
        )

        client = ServicetradeClient(username="user", password="wrong")

        with pytest.raises(ServicetradeAuthError) as exc_info:
            client.login()

        assert exc_info.value.status_code == 401


class TestLogout:
    """Test logout functionality."""

    @responses.activate
    def test_logout_clears_token(self):
        """Should clear the authentication token."""
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
        """Should call on_unset_auth callback."""
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
        """Should not raise error if token revocation fails."""
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
        """Should make GET request."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/job/123",
            json={"data": {"id": 123, "name": "Test Job"}},
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.get("/job/123")

        assert result == {"id": 123, "name": "Test Job"}

    @responses.activate
    def test_post_request(self):
        """Should make POST request with data."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/jobitem",
            json={"data": {"id": 456}},
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.post("/jobitem", {"name": "New Item"})

        assert result == {"id": 456}

    @responses.activate
    def test_put_request(self):
        """Should make PUT request with data."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.PUT,
            f"{BASE_URL}{API_PREFIX}/jobitem/456",
            json={"data": {"id": 456, "updated": True}},
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.put("/jobitem/456", {"name": "Updated Item"})

        assert result == {"id": 456, "updated": True}

    @responses.activate
    def test_delete_request(self):
        """Should make DELETE request."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.DELETE,
            f"{BASE_URL}{API_PREFIX}/job/123",
            json={"data": {"deleted": True}},
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.delete("/job/123")

        assert result == {"deleted": True}

    @responses.activate
    def test_returns_none_for_empty_data(self):
        """Should return None if response has no data."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/empty",
            body="",
            status=204,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.get("/empty")

        assert result is None

    @responses.activate
    def test_returns_list_response(self):
        """Should return list responses directly (not wrapped in data)."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/items",
            json=[{"id": 1}, {"id": 2}, {"id": 3}],
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.get("/items")

        assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


class TestAutoRefresh:
    """Test automatic token refresh."""

    @responses.activate
    def test_refreshes_on_401(self):
        """Should automatically refresh token on 401 response."""
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

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        result = client.get("/job/123")

        assert result == {"id": 123}
        assert client._token == new_token

    @responses.activate
    def test_refreshes_stale_token_before_request(self):
        """Should refresh token before request if about to expire."""
        # Create an expired token
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
            token=expired_token, username="user", password="pass"
        )
        result = client.get("/job/123")

        assert result == {"id": 123}
        assert client._token == new_token


class TestFileAttachment:
    """Test file attachment functionality."""

    @responses.activate
    def test_attach_file(self):
        """Should upload file attachment."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/attachment",
            json={"data": {"id": 789, "filename": "test.txt"}},
            status=200,
        )

        client = ServicetradeClient(username="user", password="pass")
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
        """Should include custom headers in requests."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )

        def request_callback(request):
            assert request.headers.get("X-Custom-Header") == "custom-value"
            return (200, {}, json.dumps({"data": {"success": True}}))

        responses.add_callback(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/test",
            callback=request_callback,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()
        client.set_custom_header("X-Custom-Header", "custom-value")
        result = client.get("/test")

        assert result == {"success": True}

    @responses.activate
    def test_custom_user_agent(self):
        """Should use custom user agent."""
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
            username="user",
            password="pass",
            user_agent="Custom/1.0",
        )
        client.login()


class TestErrorHandling:
    """Test error handling."""

    @responses.activate
    def test_api_error_includes_status_code(self):
        """Should include status code in API errors."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}{API_PREFIX}/notfound",
            json={"error": "Not found"},
            status=404,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()

        with pytest.raises(ServicetradeAPIError) as exc_info:
            client.get("/notfound")

        assert exc_info.value.status_code == 404

    @responses.activate
    def test_api_error_includes_response_data(self):
        """Should include response data in API errors."""
        token = create_mock_token()
        responses.add(
            responses.POST,
            f"{BASE_URL}/oauth2/token",
            json={"access_token": token},
            status=200,
        )
        responses.add(
            responses.POST,
            f"{BASE_URL}{API_PREFIX}/invalid",
            json={"error": "Validation failed", "details": ["field required"]},
            status=400,
        )

        client = ServicetradeClient(username="user", password="pass")
        client.login()

        with pytest.raises(ServicetradeAPIError) as exc_info:
            client.post("/invalid", {})

        assert exc_info.value.response_data is not None
        assert exc_info.value.response_data.get("error") == "Validation failed"
