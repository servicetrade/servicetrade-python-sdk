"""Custom exceptions for the ServiceTrade Python SDK."""

from typing import Any, List, Optional


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
        self.error_messages: List[str] = []
        self.validation: List[str] = []

        # Parse structured error format from ServiceTrade API
        if isinstance(response_data, dict):
            messages = response_data.get("messages", {})
            if isinstance(messages, dict):
                errors = messages.get("error", [])
                if isinstance(errors, list):
                    self.error_messages = [str(e) for e in errors]
                elif isinstance(errors, str):
                    self.error_messages = [errors]

                validations = messages.get("validation", [])
                if isinstance(validations, list):
                    self.validation = [str(v) for v in validations]
                elif isinstance(validations, str):
                    self.validation = [validations]

        # Build a better message from structured errors if available
        if self.error_messages or self.validation:
            parts = []
            if self.error_messages:
                parts.append("Errors: " + "; ".join(self.error_messages))
            if self.validation:
                parts.append("Validation: " + "; ".join(self.validation))
            message = " | ".join(parts)

        super().__init__(message, *args)
