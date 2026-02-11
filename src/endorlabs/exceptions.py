"""Custom exception classes for Endor Labs SDK.

These exceptions provide structured error handling and allow callers to
distinguish between different types of API errors.
"""

from typing import Any, override

from .types import ErrorResponse


class EndorAPIError(Exception):
    """Base exception for Endor API errors.

    All API-related errors should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_response: ErrorResponse | None = None,
        response_text: str | None = None,
        operation: str | None = None,
        resource_uuid: str | None = None,
        namespace: str | None = None,
    ) -> None:
        """Initialize EndorAPIError.

        Args:
            message: Human-readable error message
            status_code: HTTP status code if available
            error_response: Structured error response if available
            response_text: Raw response text if available
            operation: Operation that failed (e.g., 'create', 'update', 'delete')
            resource_uuid: UUID of the resource involved in the operation
            namespace: Namespace where the operation was attempted

        """
        super().__init__(message)
        self.status_code = status_code
        self.error_response = error_response
        self.response_text = response_text
        self.operation = operation
        self.resource_uuid = resource_uuid
        self.namespace = namespace

    @property
    def message(self) -> str:
        """Human-readable error message (aligns with API error body 'message' field)."""
        return self.args[0] if self.args else ""

    @override
    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [super().__str__()]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.resource_uuid:
            parts.append(f"Resource UUID: {self.resource_uuid}")
        if self.namespace:
            parts.append(f"Namespace: {self.namespace}")
        return " | ".join(parts)


class NotFoundError(EndorAPIError):
    """Resource not found (404).

    Raised when the resource does not exist to the user — e.g. a different
    namespace that the credential does not have access to, or the resource
    no longer exists.
    """

    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, status_code=404, **kwargs)


class AmbiguousError(EndorAPIError):
    """Multiple resources match (lookup ambiguity).

    Raised when a lookup by identity (e.g. name) returns more than one
    resource and a single result was expected.
    """

    def __init__(
        self,
        message: str = "Multiple resources match; narrow the query",
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=None, **kwargs)


class ValidationError(EndorAPIError):
    """Validation error (400).

    Raised when request validation fails
    (invalid parameters, missing required fields, etc.).
    """

    def __init__(self, message: str = "Validation error", **kwargs: Any) -> None:
        super().__init__(message, status_code=400, **kwargs)


class PermissionDeniedError(EndorAPIError):
    """Permission denied (403).

    Raised when the user doesn't have permission to perform the requested operation.
    """

    def __init__(self, message: str = "Permission denied", **kwargs: Any) -> None:
        super().__init__(message, status_code=403, **kwargs)


class UnauthorizedError(EndorAPIError):
    """Unauthorized (401).

    Raised when authentication fails or credentials are invalid.
    """

    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        super().__init__(message, status_code=401, **kwargs)


class ConflictError(EndorAPIError):
    """Conflict error (409).

    Raised when the request conflicts with the current state of the resource.
    """

    def __init__(self, message: str = "Conflict", **kwargs: Any) -> None:
        super().__init__(message, status_code=409, **kwargs)


class RateLimitError(EndorAPIError):
    """Rate limit exceeded (429).

    Raised when too many requests have been made in a short period.
    """

    def __init__(self, message: str = "Rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(message, status_code=429, **kwargs)


class ServerError(EndorAPIError):
    """Server error (500, 502, 503, 504).

    Raised when the server encounters an error processing the request.
    """

    def __init__(self, message: str = "Server error", **kwargs: Any) -> None:
        status_code = kwargs.pop("status_code", 500)
        super().__init__(message, status_code=status_code, **kwargs)


class NetworkError(EndorAPIError):
    """Network error (connection failures, timeouts).

    Raised when network-related errors occur (connection failures, timeouts).
    These errors are automatically retried with exponential backoff.
    """

    def __init__(self, message: str = "Network error", **kwargs: Any) -> None:
        status_code = kwargs.pop("status_code", None)
        super().__init__(message, status_code=status_code, **kwargs)


class MethodNotSupportedError(EndorAPIError):
    """Method not implemented (501).

    Raised when the API endpoint doesn't support the requested operation.
    This is a permanent client error, not a transient server error.
    """

    def __init__(self, message: str = "Method not implemented", **kwargs: Any) -> None:
        _ = kwargs.pop("status_code", None)
        super().__init__(message, status_code=501, **kwargs)


# Backward-compatible alias — deprecated; use MethodNotSupportedError instead.
NotImplementedError = MethodNotSupportedError


def map_status_code_to_exception(
    status_code: int,
    message: str | None = None,
    **kwargs: Any,
) -> EndorAPIError:
    """Map HTTP status code to appropriate exception class.

    Args:
        status_code: HTTP status code
        message: Optional error message
        **kwargs: Additional arguments to pass to exception constructor

    Returns:
        Appropriate exception instance

    """
    if status_code == 404:
        return NotFoundError(message or "Resource not found", **kwargs)
    elif status_code == 400:
        return ValidationError(message or "Validation error", **kwargs)
    elif status_code == 403:
        return PermissionDeniedError(message or "Permission denied", **kwargs)
    elif status_code == 401:
        return UnauthorizedError(message or "Unauthorized", **kwargs)
    elif status_code == 409:
        return ConflictError(message or "Conflict", **kwargs)
    elif status_code == 429:
        return RateLimitError(message or "Rate limit exceeded", **kwargs)
    elif status_code == 501:
        return MethodNotSupportedError(message or "Method not implemented", **kwargs)
    elif status_code in (500, 502, 503, 504):
        return ServerError(message or "Server error", status_code=status_code, **kwargs)
    else:
        return EndorAPIError(
            message or f"API error (status {status_code})",
            status_code=status_code,
            **kwargs,
        )
