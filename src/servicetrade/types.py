"""Type definitions for the ServiceTrade Python SDK."""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

# Type alias for bearer token
BearerToken = str

# Type alias for API responses - can be a dict or a list of dicts
ServicetradeClientResponse = Union[dict[str, Any], list[Any]]


@dataclass
class FileAttachment:
    value: Union[bytes, io.IOBase, Path]
    filename: str
    content_type: Optional[str] = None

    def get_tuple(self) -> tuple:
        """Return a tuple suitable for requests file upload."""
        file_content = self.value
        if isinstance(self.value, Path):
            file_content = self.value.read_bytes()
        elif isinstance(self.value, io.IOBase):
            file_content = self.value.read()

        if self.content_type:
            return (self.filename, file_content, self.content_type)
        return (self.filename, file_content)


@dataclass
class ServicetradeClientOptions:
    base_url: str = "https://api.servicetrade.com"
    api_prefix: str = "/api"
    user_agent: str = "Servicetrade Python SDK"
    auto_refresh_auth: bool = True
    on_set_auth: Optional[Callable[[BearerToken], None]] = None
    on_unset_auth: Optional[Callable[[], None]] = None
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    token: Optional[BearerToken] = None
    custom_headers: dict[str, str] = field(default_factory=dict)

    def has_password_credentials(self) -> bool:
        """Check if username/password credentials are provided."""
        return self.username is not None and self.password is not None

    def has_client_credentials(self) -> bool:
        """Check if client credentials are provided."""
        return self.client_id is not None and self.client_secret is not None

    def has_refresh_token(self) -> bool:
        """Check if a refresh token is provided."""
        return self.refresh_token is not None

    def has_any_credentials(self) -> bool:
        """Check if any form of credentials are provided."""
        return (
            self.has_password_credentials()
            or self.has_client_credentials()
            or self.has_refresh_token()
            or self.token is not None
        )


@dataclass
class Credentials:

    grant_type: str
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary, excluding None values."""
        result = {"grant_type": self.grant_type}
        if self.refresh_token is not None:
            result["refresh_token"] = self.refresh_token
        if self.client_id is not None:
            result["client_id"] = self.client_id
        if self.client_secret is not None:
            result["client_secret"] = self.client_secret
        if self.username is not None:
            result["username"] = self.username
        if self.password is not None:
            result["password"] = self.password
        return result
