"""Custom exceptions for the ServiceTrade Python SDK."""

from typing import Any, Optional


class ServicetradeError(Exception):
    """Base exception for all ServiceTrade SDK errors."""

    def __init__(self, message: str, *args: Any) -> None:
        self.message = message
        super().__init__(message, *args)


class ServicetradeAuthError(ServicetradeError):
    """Exception raised for authentication-related errors."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, *args: Any
    ) -> None:
        self.status_code = status_code
        super().__init__(message, *args)


class ServicetradeAPIError(ServicetradeError):
    """Exception raised for API request errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Any] = None,
        *args: Any,
    ) -> None:
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message, *args)
