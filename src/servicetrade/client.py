import base64
import json
import time
from typing import Any, Callable, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import ServicetradeAPIError, ServicetradeAuthError
from .types import (
    BearerToken,
    Credentials,
    FileAttachment,
    ServicetradeClientOptions,
    ServicetradeClientResponse,
)

# Token TTL buffer in seconds (5 minutes)
TOKEN_TTL_BUFFER_SECONDS = 300


class ServicetradeClient:
    def __init__(
        self,
        base_url: str = "https://api.servicetrade.com",
        api_prefix: str = "/api",
        user_agent: str = "Servicetrade Python SDK",
        auto_refresh_auth: bool = True,
        on_set_auth: Optional[Callable[[BearerToken], None]] = None,
        on_unset_auth: Optional[Callable[[], None]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token: Optional[BearerToken] = None,
        **kwargs: Any,
    ) -> None:
        self._options = ServicetradeClientOptions(
            base_url=base_url,
            api_prefix=api_prefix,
            user_agent=user_agent,
            auto_refresh_auth=auto_refresh_auth,
            on_set_auth=on_set_auth,
            on_unset_auth=on_unset_auth,
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            token=token,
        )

        # Validate credentials
        if not self._options.has_any_credentials():
            raise ServicetradeAuthError(
                "Username and password or clientId and clientSecret are required"
            )

        # Store credentials for refresh - prioritize refresh token
        self._credentials: Optional[Credentials] = None
        self._setup_credentials()

        # Current token
        self._token: Optional[BearerToken] = token
        self._token_expiry: Optional[float] = None

        # Create sessions
        self._session = self._create_session()
        self._auth_session = self._create_session()

        # Custom headers
        self._custom_headers: dict[str, str] = {}

    def _setup_credentials(self) -> None:
        """Set up credentials for authentication, prioritizing refresh token."""
        if self._options.has_refresh_token():
            self._credentials = Credentials(
                grant_type="refresh_token",
                refresh_token=self._options.refresh_token,
            )
        elif self._options.has_client_credentials():
            self._credentials = Credentials(
                grant_type="client_credentials",
                client_id=self._options.client_id,
                client_secret=self._options.client_secret,
            )
        elif self._options.has_password_credentials():
            self._credentials = Credentials(
                grant_type="password",
                username=self._options.username,
                password=self._options.password,
            )

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self, include_auth: bool = True) -> dict[str, str]:
        """Get headers for requests."""
        headers = {
            "User-Agent": self._options.user_agent,
            "Content-Type": "application/json",
            **self._custom_headers,
        }
        if include_auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _parse_token_expiry(self, token: str) -> Optional[float]:
        try:
            # JWT has 3 parts separated by dots
            parts = token.split(".")
            if len(parts) != 3:
                return None

            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding

            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)

            exp = data.get("exp")
            return float(exp) if exp is not None else None
        except Exception:
            # If we can't parse, treat as valid to avoid auth spam
            return None

    def _is_token_stale(self) -> bool:
        """Check if the current token is stale (expired or about to expire)."""
        if not self._token:
            return True

        if self._token_expiry is None:
            self._token_expiry = self._parse_token_expiry(self._token)

        if self._token_expiry is None:
            # Can't determine expiry, assume valid
            return False

        # Check if token expires within the buffer period
        return time.time() >= (self._token_expiry - TOKEN_TTL_BUFFER_SECONDS)

    def _refresh_if_stale(self) -> None:
        """Refresh the token if it's stale."""
        if self._options.auto_refresh_auth and self._is_token_stale():
            self.login()

    def set_custom_header(self, key: str, value: str) -> None:
        self._custom_headers[key] = value

    def login(self) -> BearerToken:
        if not self._credentials:
            raise ServicetradeAuthError("No credentials available for authentication")

        url = f"{self._options.base_url}/oauth2/token"
        headers = {
            "User-Agent": self._options.user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            response = self._auth_session.post(
                url,
                data=self._credentials.to_dict(),
                headers=headers,
            )
            response.raise_for_status()

            data = response.json()
            self._token = data.get("access_token")
            self._token_expiry = None  # Reset to force re-parsing

            # Update refresh token if provided
            new_refresh_token = data.get("refresh_token")
            if new_refresh_token and self._credentials.grant_type == "refresh_token":
                self._credentials.refresh_token = new_refresh_token

            # Call callback if provided
            if self._options.on_set_auth and self._token:
                self._options.on_set_auth(self._token)

            return self._token

        except requests.exceptions.HTTPError as e:
            status_code = None
            if e.response is not None:
                status_code = e.response.status_code
            raise ServicetradeAuthError(
                f"Authentication failed: {str(e)}",
                status_code=status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            raise ServicetradeAuthError(
                f"Authentication request failed: {str(e)}"
            ) from e

    def logout(self) -> None:
        # Clear the token
        self._token = None
        self._token_expiry = None

        # Attempt to revoke refresh token (suppress errors)
        if self._credentials and self._credentials.refresh_token:
            try:
                url = f"{self._options.base_url}/oauth2/revoke"
                headers = {
                    "User-Agent": self._options.user_agent,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                self._auth_session.post(
                    url,
                    data={"token": self._credentials.refresh_token},
                    headers=headers,
                )
            except Exception:
                # Suppress revoke errors to allow graceful logout
                pass

        # Call callback if provided
        if self._options.on_unset_auth:
            self._options.on_unset_auth()

    def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Any] = None,
        files: Optional[dict[str, Any]] = None,
    ) -> Optional[ServicetradeClientResponse]:
        self._refresh_if_stale()

        url = f"{self._options.base_url}{self._options.api_prefix}{path}"
        headers = self._get_headers()

        # Remove Content-Type for multipart requests
        if files:
            headers.pop("Content-Type", None)

        try:
            if method == "GET":
                response = self._session.get(url, headers=headers)
            elif method == "POST":
                if files:
                    response = self._session.post(
                        url, headers=headers, data=data, files=files
                    )
                else:
                    response = self._session.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = self._session.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = self._session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle 401 with auto-refresh
            if response.status_code == 401 and self._options.auto_refresh_auth:
                self.login()
                headers = self._get_headers()
                # Retry the request
                if method == "GET":
                    response = self._session.get(url, headers=headers)
                elif method == "POST":
                    if files:
                        response = self._session.post(
                            url, headers=headers, data=data, files=files
                        )
                    else:
                        response = self._session.post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = self._session.put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = self._session.delete(url, headers=headers)

            response.raise_for_status()

            # Handle empty responses
            if not response.content:
                return None

            response_data = response.json()

            # Unpack nested data if present (matching Node SDK behavior)
            if isinstance(response_data, dict) and "data" in response_data:
                return response_data["data"]

            # Return dict or list responses directly
            if isinstance(response_data, (dict, list)):
                return response_data

            return None

        except requests.exceptions.HTTPError as e:
            status_code = None
            response_data = None
            if e.response is not None:
                status_code = e.response.status_code
                try:
                    response_data = e.response.json()
                except Exception:
                    pass
            raise ServicetradeAPIError(
                f"API request failed: {str(e)}",
                status_code=status_code,
                response_data=response_data,
            ) from e
        except requests.exceptions.RequestException as e:
            raise ServicetradeAPIError(f"Request failed: {str(e)}") from e

    def get(self, path: str) -> Optional[ServicetradeClientResponse]:
        return self._make_request("GET", path)

    def post(self, path: str, data: Any = None) -> Optional[ServicetradeClientResponse]:
        return self._make_request("POST", path, data=data)

    def put(self, path: str, data: Any = None) -> Optional[ServicetradeClientResponse]:
        return self._make_request("PUT", path, data=data)

    def delete(self, path: str) -> Optional[ServicetradeClientResponse]:
        return self._make_request("DELETE", path)

    def attach(
        self,
        params: dict[str, Any],
        file: FileAttachment,
    ) -> Optional[ServicetradeClientResponse]:
        files = {"file": file.get_tuple()}
        return self._make_request("POST", "/attachment", data=params, files=files)
