"""API Client for Endor Labs REST API.

    Provides REST calls with retry, rate limiting, pagination,
    and logging with redaction.

Author:
    tgowan@endor.ai
"""

import html
import logging
import os
import re
import time
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from .exceptions import (
    EndorAPIError,
    map_status_code_to_exception,
)
from .types import ErrorResponse
from .utils.redaction import RedactingFilter, redaction_pattern

ENDOR_NAMESPACE = os.getenv("ENDOR_NAMESPACE")
# TODO: Determine if needed or as an init param or env var


class APIClient:
    """Minimal API client with retry, rate limiting handling and redacted logging.

    Retry Behavior:
        The client automatically retries requests for network-related errors and
        specific HTTP status codes. Retries use exponential backoff.

        Retryable Errors:
        - Network errors: ConnectionError, Timeout (all retried automatically)
        - HTTP 429 (Rate Limit): Retried with exponential backoff, respects
          Retry-After header
        - HTTP 500, 502, 503, 504 (Server Errors): Retried as transient server issues

        Non-Retryable Errors (Graceful Exit):
        - HTTP 400 (Validation Error): Client error, not retried
        - HTTP 401 (Unauthorized): Single retry after reauthentication, then exit
        - HTTP 403 (Permission Denied): Client error, not retried
        - HTTP 404 (Not Found): Client error, not retried
        - HTTP 409 (Conflict): Client error, not retried

        Retry Limits:
        - Default max_retries: 5 (configurable via ENDOR_MAX_RETRIES env var)
        - Backoff factor: 0.5 (exponential: 0.5s, 1s, 2s, 4s, 8s)
        - Maximum retry time: ~16 seconds for 5 retries

    Args:
        max_retries: Maximum number of retries for requests. Default: 5.
            If not provided, uses ENDOR_MAX_RETRIES environment variable.
            If neither provided, defaults to 5.
            Reduces excessive retry time on persistent network issues.
        backoff_factor: Backoff factor for retries. Default: 0.5.
        status_forcelist: HTTP status codes that trigger a retry.
            Default: (429, 500, 502, 503, 504). Network errors are always retried.
        logging_level: Logging level for the client's logger.
            If None, uses ENDOR_LOG_LEVEL environment variable.
            Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL.
        base_url: API base URL. If None, uses ENDOR_API env var or default.
        timeout: Request timeout in seconds. If None, uses ENDOR_REQUEST_TIMEOUT
            env var or 60.0. Also sent as Request-timeout header.
        content_type: Content-Type header value. If None, defaults to
            "application/json".
        accept_encoding: Accept-Encoding header value. If None or "", the header
            is omitted. Otherwise the given string is sent.
        key: API credentials key. If None, uses ENDOR_API_CREDENTIALS_KEY env var.
        secret: API credentials secret. If None, uses ENDOR_API_CREDENTIALS_SECRET.
        token: Bearer token. If None, uses ENDOR_TOKEN env var.
        auth_method: Auth method (e.g. "api-key", "browser"). If None, uses env/default.
        email: Email for auth. Optional.

    The client can be used as a context manager (with APIClient(...) as client:).
    When not using ``with``, call close() when done to release connections.

    """

    client: httpx.Client | None  # Set in __init__; set to None in close().

    def __init__(
        self,
        max_retries: int = 5,
        backoff_factor: float = 0.5,
        status_forcelist: tuple[int, ...] = (429, 500, 502, 503, 504),
        logging_level: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        content_type: str | None = None,
        accept_encoding: str | None = None,
        key: str | None = None,
        secret: str | None = None,
        token: str | None = None,
        auth_method: str | None = None,
        email: str | None = None,
    ) -> None:
        super().__init__()
        # Set up logging
        from endorlabs.utils.logging_config import (
            apply_client_session_log_level,
            setup_logging,
        )

        self.logger = setup_logging("endorlabs")
        self.logger.addFilter(RedactingFilter([redaction_pattern]))

        # Set log level with precedence: parameter > env var > default
        # setup_logging already handles env var (ENDOR_LOG_LEVEL),
        # so we only override if parameter is explicitly provided
        if logging_level is not None:
            # Parameter takes highest precedence; apply to all session loggers
            level = logging_level.upper()
            numeric_level = getattr(logging, level, logging.INFO)
            self.logger.setLevel(numeric_level)
            apply_client_session_log_level(numeric_level)

        # Initialize API client parameters
        # Precedence: parameters > environment variables > defaults
        self.base_url = (
            base_url or os.getenv("ENDOR_API") or "https://api.endorlabs.com"
        )

        # Determine authentication method
        # Precedence: parameter > env var > default (api-key)
        self.auth_method = auth_method or os.getenv("ENDOR_AUTH_METHOD") or "api-key"

        # Get token if provided directly
        self._provided_token = token or os.getenv("ENDOR_TOKEN")

        # For browser auth, check if token is "browser" to trigger OAuth flow
        if self._provided_token == "browser" or self.auth_method in [
            "browser",
            "admin",
            "google",
            "github",
            "gitlab",
            "email",
        ]:
            # Browser-based authentication
            self.key = None
            self.secret = None
            self._auth_type = "browser"
        else:
            # API key authentication (default). Param > env.
            self.key = key or os.getenv("ENDOR_API_CREDENTIALS_KEY")
            self.secret = secret or os.getenv("ENDOR_API_CREDENTIALS_SECRET")
            self._auth_type = "api-key"

            if not self.key or not self.secret:
                error_msg = (
                    "API credentials not found. Please provide credentials via:\n"
                    "  - Constructor: APIClient(key=..., secret=...)\n"
                    "  - Environment variables: ENDOR_API_CREDENTIALS_KEY and "
                    "ENDOR_API_CREDENTIALS_SECRET\n"
                    "  - Or use browser authentication: "
                    "APIClient(auth_method='browser')"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # Store browser auth parameters
        self._browser_name = os.getenv("ENDOR_BROWSER")
        self._email = email

        # Initialize token expiration tracking
        self._token: str | None = None
        self._token_expires: datetime | None = None

        # Get max_retries with precedence: parameter > env var > default
        # If max_retries is the default (5), check env var; otherwise use provided value
        if max_retries == 5:
            # Check if env var is set, otherwise use default 5
            env_max_retries = os.getenv("ENDOR_MAX_RETRIES")
            if env_max_retries is not None:
                max_retries = int(env_max_retries)
        # else: max_retries was explicitly provided (not default), use it

        # Store retry configuration for error messages and retry loop
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist

        # Timeout: parameter > ENDOR_REQUEST_TIMEOUT env > default 60.0
        if timeout is not None:
            self.timeout = float(timeout)
        else:
            env_timeout = os.getenv("ENDOR_REQUEST_TIMEOUT")
            self.timeout = float(env_timeout) if env_timeout else 60.0

        # Content-Type: parameter > default "application/json"
        self.content_type = (
            content_type if content_type is not None else "application/json"
        )

        # Accept-Encoding: parameter only; None or "" means omit header
        self.accept_encoding = accept_encoding

        # Request headers (merged with per-request headers); updated after auth
        self._request_headers = {"Content-Type": self.content_type}
        self._request_headers["Request-timeout"] = str(int(self.timeout))
        if self.accept_encoding:
            self._request_headers["Accept-Encoding"] = self.accept_encoding

        # Initialize httpx client (no built-in retry; we use _request_with_retry)
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._request_headers.copy(),
        )
        self.rate_limit_delay = 0
        self.last_request_time = 0
        self.logger_len = 25

        # Authenticate and set initial headers
        # Use token property to ensure fresh token with expiration tracking
        _ = self.token
        if self._token:
            self._request_headers["Authorization"] = f"Bearer {self._token}"
        self.default_headers = self._headers_copy()

    def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        client = self.client
        if client is not None:
            client.close()
            self.client = None

    def __enter__(self) -> "APIClient":
        """Enter context manager; return self."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager; close the client. Do not suppress exceptions."""
        self.close()
        return None

    def _rate_limit(self) -> None:
        """Apply a delay if a rate limit was previously encountered."""
        if self.rate_limit_delay > 0:
            wait_time = self.rate_limit_delay - (time.time() - self.last_request_time)
            if wait_time > 0:
                self.logger.warning(
                    f"Rate limit encountered. Waiting for {wait_time:.2f} seconds."
                )
                time.sleep(wait_time)
            self.rate_limit_delay = 0

    def _headers_copy(self) -> dict[str, str]:
        """Return a mutable copy of request headers with string values."""
        return dict(self._request_headers)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL: use as-is if absolute, prepend base_url if relative."""
        if url.startswith(("http://", "https://")):
            return url
        # Relative URL: prepend base_url with proper slash handling
        base = self.base_url.rstrip("/")
        url = url.lstrip("/")
        return f"{base}/{url}"

    def _redact_log_data(self, data: Any) -> str:
        """Redact sensitive data from logging."""
        if data is None:
            return "None"
        data_str = str(data)
        # Use the same redaction pattern as the filter
        pattern = re.compile(redaction_pattern, re.IGNORECASE)
        data_str = pattern.sub(r"'\1': '***REDACTED***'", data_str)
        return data_str

    def _truncate_for_logging(self, text: str, max_length: int = 500) -> str:
        """Truncate text for logging purposes only (not for error handling).

        This is used for debug logs to prevent excessive log output.
        For actual error handling, use full error text.
        """
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}... (truncated, {len(text)} chars total)"

    def _parse_error_response(self, response: httpx.Response) -> str:
        """Parse error response and return full error details.

        Attempts to parse structured error response, falls back to full text.
        """
        try:
            # Try to parse as JSON first
            error_data = response.json()
            if isinstance(error_data, dict):
                err: dict[str, Any] = cast("dict[str, Any]", error_data)
                # Try to extract structured error information
                error_msg: str = (
                    err.get("message")
                    or err.get("error")
                    or str(cast("Any", error_data))
                )
                error_code: int | str = err.get("code") or response.status_code
                error_details: Any = err.get("details")

                result = f"Error {error_code}: {error_msg}"
                if error_details:
                    result += f"\nDetails: {error_details}"
                return result
            return str(error_data)
        except (ValueError, AttributeError):
            # If JSON parsing fails, return full text
            return response.text

    def _extract_grpc_code(self, error_data: dict[str, Any]) -> int | None:
        """Extract gRPC code from error data.

        Tries multiple methods:
        1. Direct numeric "code" field
        2. Parse error string (e.g., "invalid-args" -> 3, "not-found" -> 5)
        """
        # Method 1: Try direct numeric code field
        grpc_code = error_data.get("code")
        if grpc_code is not None:
            if isinstance(grpc_code, int):
                return grpc_code
            # Try to convert string to int
            try:
                return int(grpc_code)
            except (ValueError, TypeError):
                pass

        # Method 2: Parse error string to gRPC code
        error_str = error_data.get("error", "").lower()
        error_to_code_map = {
            "invalid-args": 3,  # INVALID_ARGUMENT
            "invalid_argument": 3,
            "not-found": 5,  # NOT_FOUND
            "not_found": 5,
            "permission-denied": 7,  # PERMISSION_DENIED
            "permission_denied": 7,
            "unauthenticated": 16,  # UNAUTHENTICATED
            "already-exists": 6,  # ALREADY_EXISTS
            "already_exists": 6,
            "unavailable": 14,  # UNAVAILABLE
            "internal": 13,  # INTERNAL
            "deadline-exceeded": 4,  # DEADLINE_EXCEEDED
            "deadline_exceeded": 4,
            "unknown": 2,  # UNKNOWN
            "cancelled": 1,  # CANCELLED
        }

        if error_str in error_to_code_map:
            return error_to_code_map[error_str]

        return None

    def _extract_error_message(self, error_data: dict[str, Any]) -> str | None:
        """Extract and clean error message."""
        error_msg = error_data.get("message") or error_data.get("error")
        if not error_msg:
            return None

        # Decode HTML entities
        error_msg = html.unescape(error_msg)

        # Remove "Error X:" prefix if present
        if error_msg.startswith("Error "):
            error_msg = re.sub(r"^Error \d+:\s*", "", error_msg)

        return error_msg

    def _parse_invalid_path_error(self, error_msg: str) -> str | None:
        """Parse 'invalid path' errors specifically."""
        if "invalid path" not in error_msg:
            return None

        match = re.search(r"invalid path\s+['\"]([^'\"]+)['\"]", error_msg)
        if match:
            return f"Invalid filter path: '{match.group(1)}'"
        return None

    def _parse_error_response_succinct(
        self, response: httpx.Response
    ) -> tuple[int | None, str]:
        """Parse error response and return gRPC code and succinct message.

        Extracts the actionable error message, decodes HTML entities,
        and removes verbose technical details. Also extracts gRPC status code.

        Returns:
            Tuple of (grpc_code, error_message)
            - grpc_code: gRPC status code if available, None otherwise
            - error_message: Succinct, user-friendly error message

        """
        try:
            # Try to parse as JSON first
            error_data = response.json()
            if isinstance(error_data, dict):
                err = cast("dict[str, Any]", error_data)
                grpc_code = self._extract_grpc_code(err)
                error_msg = self._extract_error_message(err)

                if error_msg:
                    # Check for invalid path errors first
                    invalid_path_msg = self._parse_invalid_path_error(error_msg)
                    if invalid_path_msg:
                        return (grpc_code, invalid_path_msg)
                    return (grpc_code, error_msg)

                # Fallback to string representation
                return (grpc_code, str(err))
        except (ValueError, AttributeError):
            pass

        # If JSON parsing fails, try to extract from text
        text = response.text
        if text:
            # Decode HTML entities
            text = html.unescape(text)
            # Try to extract meaningful error message
            invalid_path_msg = self._parse_invalid_path_error(text)
            if invalid_path_msg:
                return (None, invalid_path_msg)
            return (None, text)
        return (None, f"HTTP {response.status_code} error")

    def _get_grpc_error_context(self, grpc_code: int) -> tuple[int | None, str, str]:
        """Get error context for documented gRPC codes.

        Maps documented gRPC status codes to HTTP status codes,
        error context descriptions, and user-friendly messages.

        Args:
            grpc_code: gRPC status code

        Returns:
            Tuple of (http_status_code, error_context, user_message)
            - http_status_code: HTTP status code if documented, None otherwise
            - error_context: Human-readable error context description
            - user_message: User-friendly error message (if documented)

        """
        # Map documented gRPC codes based on Endor Labs documentation
        # and Go test file (status_test.go)
        grpc_code_map = {
            1: (  # CANCELLED
                408,
                "Request cancelled",
                "The command has been canceled. Please wait and try again.",
            ),
            2: (  # UNKNOWN
                500,
                "Unknown error",
                "An unknown error occurred. If this issue persists "
                "please provide feedback to Endor Labs.",
            ),
            3: (  # INVALID_ARGUMENT
                400,
                "Validation error",
                "",  # Message will be provided by specific error parsing
            ),
            4: (  # DEADLINE_EXCEEDED
                504,
                "Deadline exceeded",
                "The deadline expired before the operation could be completed. "
                "Please consider using pagination for list requests.",
            ),
            5: (  # NOT_FOUND
                404,
                "Resource not found",
                "The resource or object that you have requested does not exist. "
                "Please check your command for mistakes in resource names or spelling.",
            ),
            6: (  # ALREADY_EXISTS
                409,
                "Resource already exists",
                "You have attempted to create an object that already exists. "
                "If you would like to update that object please use the "
                "update command instead.",
            ),
            7: (  # PERMISSION_DENIED
                403,
                "Permission denied",
                "You do not have the appropriate permissions to perform "
                "this operation. Please check that you are using the correct "
                "API key and check the API key permissions.",
            ),
            13: (  # INTERNAL
                500,
                "Internal server error",
                "An internal error occurred. It's not you, it's us. "
                "Please try again or contact Endor Labs for support.",
            ),
            14: (  # UNAVAILABLE
                503,
                "Service unavailable",
                "The service is currently unavailable. "
                "Please wait and try again or contact Endor Labs for support.",
            ),
            16: (  # UNAUTHENTICATED
                401,
                "Authentication failed",
                "You have not successfully authenticated in order to complete "
                "this operation. Please pass an API key and secret as an "
                "environment variable or argument or run the command "
                "endorctl init.",
            ),
        }

        if grpc_code in grpc_code_map:
            http_code, context, user_msg = grpc_code_map[grpc_code]
            return (http_code, context, user_msg)

        # Undocumented gRPC code - return None to trigger fallback
        return (None, "", "")

    def parse_error_response_structured(
        self, response: httpx.Response
    ) -> ErrorResponse | None:
        """Parse error response into structured ErrorResponse format.

        Returns ErrorResponse dict if parsing succeeds, None otherwise.
        """
        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                err = cast("dict[str, Any]", error_data)
                return ErrorResponse(
                    error=err.get("error", "Unknown error"),
                    message=err.get("message", str(err)),
                    code=err.get("code", response.status_code),
                    details=err.get("details"),
                )
        except (ValueError, AttributeError, TypeError):
            # If parsing fails, return None
            pass
        return None

    def map_http_error_to_exception(
        self,
        error: httpx.HTTPStatusError,
        operation: str,
        namespace: str,
        resource_uuid: str | None = None,
    ) -> EndorAPIError:
        """Map HTTP error to typed exception with full context.

        Uses gRPC codes first for precise error classification, matching
        server-side error semantics. Falls back to HTTP status codes for
        undocumented gRPC codes.

        Args:
            error: HTTPStatusError from httpx (has .response)
            operation: Operation that failed (e.g., 'create', 'update', 'delete')
            namespace: Namespace where the operation was attempted
            resource_uuid: Optional UUID of the resource involved

        Returns:
            Appropriate EndorAPIError subclass with full context

        """
        response = error.response
        http_status_code = response.status_code

        # Parse structured error response if available
        error_response = self.parse_error_response_structured(response)

        # Extract gRPC code and error message (gRPC codes are more precise)
        grpc_code, error_message = self._parse_error_response_succinct(response)

        # Use gRPC code to determine exception type if available
        if grpc_code is not None:
            grpc_http_code, _, _ = self._get_grpc_error_context(grpc_code)
            if grpc_http_code is not None:
                # Use HTTP status code derived from gRPC code for precision
                effective_status_code = grpc_http_code
            else:
                # Undocumented gRPC code, fall back to HTTP status
                effective_status_code = http_status_code
        else:
            # No gRPC code, use HTTP status code
            effective_status_code = http_status_code

        # Extract error message
        if not error_message:
            if error_response:
                error_message = error_response.get(
                    "message", response.text or f"HTTP {http_status_code}"
                )
            else:
                error_message = response.text or f"HTTP {http_status_code}"

        # Map to exception using the helper function with effective status code
        return map_status_code_to_exception(
            status_code=effective_status_code,
            message=error_message,
            error_response=error_response,
            response_text=response.text,
            operation=operation,
            resource_uuid=resource_uuid,
            namespace=namespace,
        )

    def _ensure_authenticated(self) -> None:
        """Ensure token is fresh and session headers are updated.

        This method should be called before making API requests to ensure
        the token is valid and headers are up to date.
        """
        # Access token property to trigger refresh if needed
        current_token = self.token
        if current_token:
            self._request_headers["Authorization"] = f"Bearer {current_token}"

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform request with retry on connection/timeout and retryable status."""
        assert self.client is not None, "APIClient is closed"
        last_exc: BaseException | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, url, **kwargs)
                self.logger.debug(
                    f"{method} response {response.status_code} - "
                    f"{self._truncate_for_logging(response.text)}"
                )
                return self._handle_response(
                    response,
                    method=method,
                    url=url,
                    **kwargs,
                )
            except httpx.HTTPStatusError as e:
                last_exc = e
                retryable = (
                    e.response.status_code in self.status_forcelist
                    and attempt < self.max_retries
                )
                if retryable:
                    backoff = self.backoff_factor * (2**attempt)
                    self.logger.warning(
                        f"Retryable status {e.response.status_code}, "
                        f"retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    time.sleep(backoff)
                    continue
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < self.max_retries:
                    backoff = self.backoff_factor * (2**attempt)
                    self.logger.warning(
                        f"Network error, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    time.sleep(backoff)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Retry loop exited without response or exception")

    def _handle_response(
        self,
        response: httpx.Response,
        method: str | None = None,
        url: str | None = None,
        **kwargs: Any,
    ) -> Any:
        self.last_request_time = time.time()
        try:
            _ = response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            status_code = response.status_code

            # Handle rate limiting (429) - retryable with backoff
            if status_code == 429:
                retry_info = response.headers.get("Retry-After", "no retry info")
                self.logger.warning(
                    f"Rate limit encountered (429): {retry_info}. "
                    f"Request to {response.url} was throttled. "
                    f"Will retry with exponential backoff."
                )
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    self.rate_limit_delay = int(retry_after) + 1
                else:
                    self.rate_limit_delay = (
                        self.rate_limit_delay if self.rate_limit_delay > 0 else 5
                    )
                raise

            # Handle authentication failure (401) - single retry after reauth
            if status_code == 401:
                self.logger.warning(
                    f"Authentication failed (401): Invalid or expired credentials. "
                    f"Request to {response.url} was unauthorized."
                )
                self.logger.info("Attempting to reauthenticate...")
                # Use authenticate() which will use the appropriate auth method
                new_token = self.authenticate()
                if new_token:
                    self._request_headers["Authorization"] = f"Bearer {new_token}"
                    self.default_headers = self._headers_copy()
                    self.logger.info("Reauthentication completed.")
                    # Retry the original request once
                    if method and url:
                        self.logger.info(f"Retrying {method} request to {url}")
                        assert self.client is not None, "APIClient is closed"
                        retry_response = self.client.request(
                            method=method, url=url, **kwargs
                        )
                        return self._handle_response(
                            retry_response, method=method, url=url, **kwargs
                        )
                raise

            # Handle 501 Not Implemented - non-retryable client error
            # (method/operation not supported, not a transient server error)
            if status_code == 501:
                error_details = self._parse_error_response(response)
                self.logger.error(
                    f"Method not implemented (501) on {method or 'UNKNOWN'} "
                    f"request to {response.url}. "
                    f"This operation is not supported by the API. "
                    f"Error: {error_details}"
                )
                raise

            # Handle server errors (5xx) - retryable
            if status_code >= 500:
                error_details = self._parse_error_response(response)
                self.logger.warning(
                    f"Server error {status_code} on {method or 'UNKNOWN'} "
                    f"request to {response.url}. "
                    f"Will retry with exponential backoff. "
                    f"Error: {error_details}"
                )
                raise

            # Handle client errors (400, 403, 404, 409) - not retried, graceful exit
            if status_code in (400, 403, 404, 409):
                error_details = self._parse_error_response(response)
                error_type = {
                    400: "Validation error",
                    403: "Permission denied",
                    404: "Resource not found",
                    409: "Conflict",
                }.get(status_code, f"Client error {status_code}")
                self.logger.error(
                    f"{error_type} ({status_code}) on {method or 'UNKNOWN'} "
                    f"request to {response.url}. "
                    f"This error will not be retried. "
                    f"Response: {error_details}"
                )
                raise

            # Other HTTP errors
            error_details = self._parse_error_response(response)
            self.logger.debug(
                f"API error {status_code} on {method or 'UNKNOWN'} "
                f"request to {response.url}: {e}. "
                f"Response: {error_details}"
            )
            raise

        except httpx.ConnectError as e:
            # Network connection errors - retryable (retry loop in _request_with_retry)
            self.logger.error(
                f"Network connection failed for {method or 'UNKNOWN'} "
                f"request to {url or 'unknown URL'}: {e}. "
                f"All {self.max_retries} retry attempts exhausted. "
                f"Check network connectivity and API endpoint availability."
            )
            raise

        except httpx.TimeoutException as e:
            # Request timeout errors - retryable (retry loop in _request_with_retry)
            self.logger.error(
                f"Request timeout exceeded for {method or 'UNKNOWN'} "
                f"request to {url or 'unknown URL'}: {e}. "
                f"All {self.max_retries} retry attempts exhausted. "
                f"Request took too long to complete."
            )
            raise

        except httpx.RequestError as e:
            # Other network-related errors - retryable
            self.logger.error(
                f"Network request failed for {method or 'UNKNOWN'} "
                f"request to {url or 'unknown URL'}: {e}. "
                f"All {self.max_retries} retry attempts exhausted. "
                f"Check network connectivity and API endpoint availability."
            )
            raise

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """GET request (httpx.Response)."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            merged_headers = self._headers_copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self._headers_copy()

        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"GET request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        return self._request_with_retry(
            "GET",
            normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def post(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """POST request (httpx.Response)."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            merged_headers = self._headers_copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self._headers_copy()

        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"POST request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        return self._request_with_retry(
            "POST",
            normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def patch(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """PATCH request (httpx.Response)."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            merged_headers = self._headers_copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self._headers_copy()

        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"PATCH request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        return self._request_with_retry(
            "PATCH",
            normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def put(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """PUT request (httpx.Response)."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            merged_headers = self._headers_copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self._headers_copy()

        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"PUT request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        return self._request_with_retry(
            "PUT",
            normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def delete(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """DELETE request (httpx.Response)."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            merged_headers = self._headers_copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self._headers_copy()

        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"DELETE request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        return self._request_with_retry(
            "DELETE",
            normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def _extract_items_from_response(self, response_data: Any) -> list[Any]:
        """Extract items from paginated response (API shape is dynamic)."""
        result: list[Any] = []
        if isinstance(response_data, dict) and "list" in response_data:
            list_data: list[Any] | dict[str, Any] = cast(
                "list[Any] | dict[str, Any]", response_data["list"]
            )
            if isinstance(list_data, dict) and "objects" in list_data:
                raw: Any = list_data["objects"]
                # API response shape is dynamic; Iterable[Any] yields list[Any]
                result = (
                    list(cast("Iterable[Any]", raw)) if isinstance(raw, list) else []
                )
        elif isinstance(response_data, list):
            result = cast("list[Any]", response_data)
        return result

    def _extract_next_page_token(self, response_data: Any) -> str | None:
        """Extract next page token from paginated response."""
        if isinstance(response_data, dict) and "list" in response_data:
            list_data: list[Any] | dict[str, Any] = cast(
                "list[Any] | dict[str, Any]", response_data["list"]
            )
            if isinstance(list_data, dict) and "response" in list_data:
                response_meta: dict[str, Any] = cast(
                    "dict[str, Any]", list_data["response"]
                )
                return response_meta.get("next_page_token")
        return None

    def _extract_next_page_id(self, response_data: Any) -> str | None:
        """Extract next page id from paginated response (list.response.next_page_id)."""
        if isinstance(response_data, dict) and "list" in response_data:
            list_data: list[Any] | dict[str, Any] = cast(
                "list[Any] | dict[str, Any]", response_data["list"]
            )
            if isinstance(list_data, dict) and "response" in list_data:
                response_meta: dict[str, Any] = cast(
                    "dict[str, Any]", list_data["response"]
                )
                raw = response_meta.get("next_page_id")
                return str(raw) if raw is not None else None
        return None

    def get_all(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        """Get all items from a paginated endpoint.

        Automatically handles page_token and page_id pagination. Yields
        individual items from paginated responses. Uses list.response.next_page_id
        when present (API-supported cursor); otherwise uses next_page_token.
        Handles Endor Labs pagination format with list.objects and list.response.

        Args:
            url: Endpoint URL (relative or absolute)
            params: Query parameters (will be updated with page_token/page_id)
            data: Request body data
            json: Request body JSON
            max_pages: Optional maximum number of pages to fetch.
                If None, fetches all pages.
            **kwargs: Additional arguments passed to request

        Yields:
            Individual items from paginated responses

        """
        normalized_url = self._normalize_url(url)
        page_token: str | None = None
        page_id: str | None = None
        page_count = 0

        # Start with provided params or empty dict
        request_params = dict(params) if params else {}

        while True:
            # Check max_pages limit before fetching page
            if max_pages is not None and page_count >= max_pages:
                self.logger.warning(
                    f"Reached max_pages limit ({max_pages}). "
                    f"Stopping pagination after {page_count} pages."
                )
                break

            # Set pagination params: page_id takes precedence when both are used
            if page_id is not None:
                request_params["list_parameters.page_id"] = page_id
                request_params.pop("list_parameters.page_token", None)
            elif page_token is not None:
                request_params["list_parameters.page_token"] = str(page_token)
                request_params.pop("list_parameters.page_id", None)
            else:
                request_params.pop("list_parameters.page_token", None)
                request_params.pop("list_parameters.page_id", None)

            # Make request
            response = self.get(
                normalized_url,
                params=request_params,
                data=data,
                json=json,
                **kwargs,
            )
            response_data = response.json()

            # Extract and yield items from this page
            items = self._extract_items_from_response(response_data)
            yield from items

            page_count += 1

            next_page_id = self._extract_next_page_id(response_data)
            next_page_token = self._extract_next_page_token(response_data)
            # Prefer page_id when API returns both (spec supports both)
            if next_page_id is not None:
                page_id = next_page_id
                page_token = None
            elif next_page_token is not None:
                page_token = next_page_token
                page_id = None
            else:
                break

        self.logger.debug(
            "Fetched all items from %s across %s pages",
            normalized_url,
            page_count,
        )

    @property
    def token(self) -> str | None:
        """Get current token, automatically refreshing if expired or about to expire.

        Returns:
            Current bearer token string, or None if authentication fails.

        """
        # If no token or token expires within 30 minutes, re-authenticate
        if self._token is None or self._token_expires is None:
            _ = self.authenticate()
        else:
            # Check if token expires within 30 minutes
            now = datetime.now(UTC)
            time_until_expiry = (self._token_expires - now).total_seconds()
            if time_until_expiry <= 30 * 60:  # 30 minutes in seconds
                _ = self.authenticate()
        return self._token

    @property
    def is_expired(self) -> bool:
        """Check if the current token is expired or about to expire.

        Returns:
            True if token is expired or expires within 60 seconds, False otherwise.

        """
        if self._token_expires is None:
            return True
        # Check if token expires within 60 seconds
        now = datetime.now(self._token_expires.tzinfo)
        time_until_expiry = (self._token_expires - now).total_seconds()
        return time_until_expiry <= 60

    def authenticate(self) -> str | None:
        """Authenticate and update session headers with bearer token.

        Supports both API key and browser-based OAuth authentication.

        Returns:
            Bearer token string or None if authentication fails.

        """
        if self._auth_type == "browser":
            return self._authenticate_browser()
        else:
            return self._authenticate_api_key()

    def _authenticate_api_key(self) -> str | None:
        """Authenticate using API key and secret."""
        assert self.client is not None, "APIClient is closed"
        try:
            payload = {"key": self.key, "secret": self.secret}
            response = self.client.post(
                "v1/auth/api-key",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            _ = response.raise_for_status()
            data = response.json()
            token = data["token"]

            # Parse expiration time from response
            expires = None
            if "expirationTime" in data:
                expires = data["expirationTime"]
            elif "expiration_time" in data:
                expires = data["expiration_time"]

            # Parse expiration datetime if present
            if expires is not None:
                try:
                    # Replace 'Z' with '+00:00' for ISO format compatibility
                    utc_datetime_str = re.sub(r"\s*Z$", "+00:00", expires)
                    self._token_expires = datetime.fromisoformat(utc_datetime_str)
                except Exception as e:
                    # If parsing fails, log but don't error out
                    self.logger.debug(
                        f"Could not parse expiration time '{expires}': {e}"
                    )
                    self._token_expires = None
            else:
                self._token_expires = None

            # Store token
            self._token = token

            # Update request headers for subsequent requests
            self._request_headers["Authorization"] = f"Bearer {token}"
            self.default_headers = self._headers_copy()
            return token
        except Exception as e:
            self.logger.error(f"Unable to authenticate with API key: {e}")
            self._token = None
            self._token_expires = None
            return None

    def _determine_browser_method(self) -> str | None:
        """Determine browser OAuth method."""
        if self._provided_token and self._provided_token != "browser":
            return None  # Direct token provided, no browser method needed
        browser_method = self.auth_method
        if browser_method == "browser":
            browser_method = "admin"  # Default to admin SSO
        return browser_method

    def _extract_environment(self) -> str:
        """Extract environment from base_url."""
        environment = self.base_url.replace("https://api.", "").replace(
            "http://api.", ""
        )
        if environment == self.base_url:
            # No api. prefix, use default
            environment = "endorlabs.com"
        return environment

    def _get_browser_token(self, browser_method: str, environment: str) -> str | None:
        """Get token from browser OAuth flow."""
        from endorlabs.auth_server import get_token as get_browser_token

        self.logger.info(f"Starting browser OAuth flow with method: {browser_method}")
        return get_browser_token(
            timeout=20,
            environment=environment,
            browser_name=self._browser_name,
            method=browser_method,
            email=self._email,
        )

    def _validate_and_store_token(self, token: str) -> None:
        """Validate token and store it."""
        assert self.client is not None, "APIClient is closed"
        # Validate token by making a test request to get expiration info
        # Some endpoints may return token metadata
        try:
            test_response = self.client.get(
                "meta/version",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            _ = test_response.raise_for_status()

            # Try to extract expiration from response if available
            # (Most endpoints don't return this, but we try)
            try:
                data = test_response.json()
                if "expirationTime" in data:
                    expires = data["expirationTime"]
                elif "expiration_time" in data:
                    expires = data["expiration_time"]
                else:
                    expires = None

                if expires is not None:
                    try:
                        utc_datetime_str = re.sub(r"\s*Z$", "+00:00", expires)
                        self._token_expires = datetime.fromisoformat(utc_datetime_str)
                    except Exception:
                        self._token_expires = None
                else:
                    # For browser tokens, we don't know expiration
                    # Set to None (will be treated as expired when checked)
                    self._token_expires = None
            except Exception:
                self._token_expires = None
        except Exception as e:
            self.logger.debug(f"Token validation request failed: {e}")
            # Token might still be valid, continue
            self._token_expires = None

        # Store token
        self._token = token

        # Update request headers for subsequent requests
        self._request_headers["Authorization"] = f"Bearer {token}"
        self.default_headers = self._headers_copy()
        self.logger.info("Browser authentication successful")

    def _authenticate_browser(self) -> str | None:
        """Authenticate using browser-based OAuth flow.

        ⚠️  WARNING: This method requires human interaction and cannot be used
        in CI/CD environments. It opens a browser window and waits for user
        authentication. Use API key authentication (ENDOR_API_CREDENTIALS_KEY
        and ENDOR_API_CREDENTIALS_SECRET) for automated environments.

        Returns:
            Bearer token string or None if authentication fails.

        """
        try:
            # Determine auth method for browser OAuth
            if self._provided_token and self._provided_token != "browser":
                # Direct token provided, validate it
                token = self._provided_token
                self.logger.info("Using provided token for authentication")
            else:
                # Trigger browser OAuth flow
                browser_method = self._determine_browser_method()
                if browser_method is None:
                    token = None
                else:
                    environment = self._extract_environment()
                    token = self._get_browser_token(browser_method, environment)

            if not token:
                self.logger.error("Browser authentication failed or was cancelled")
                self._token = None
                self._token_expires = None
                return None

            self._validate_and_store_token(token)
            return token
        except ImportError:
            self.logger.error(
                "Browser authentication requires auth_server module. "
                "This should not happen."
            )
            self._token = None
            self._token_expires = None
            return None
        except Exception as e:
            self.logger.error(f"Unable to authenticate with browser: {e}")
            self._token = None
            self._token_expires = None
            return None
