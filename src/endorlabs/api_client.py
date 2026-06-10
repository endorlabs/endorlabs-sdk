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
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from urllib.parse import urlparse

import httpx

from .core.exceptions import (
    EndorAPIError,
    ValidationError,
    map_status_code_to_exception,
)
from .core.types import ErrorResponse
from .utils.redaction import (
    JSON_REDACTION_REPLACEMENT,
    RedactingFilter,
    json_redaction_pattern,
    redaction_pattern,
    url_token_redaction_pattern,
    url_token_redaction_replacement,
)

# Pre-compiled redaction patterns for _redact_log_data (avoid re.compile per call)
_REPR_REDACT_RE: re.Pattern[str] = re.compile(redaction_pattern, re.IGNORECASE)
_JSON_REDACT_RE: re.Pattern[str] = re.compile(json_redaction_pattern, re.IGNORECASE)

# --- Token lifecycle constants -------------------------------------------
TOKEN_REFRESH_THRESHOLD_SECONDS: int = 30 * 60  # Proactive refresh 30 min before expiry
TOKEN_EXPIRY_CHECK_SECONDS: int = 60  # Considered expired if <=60 s remaining
BROWSER_AUTH_TIMEOUT_SECONDS: int = 20  # OAuth browser flow timeout
TOKEN_VALIDATION_TIMEOUT_SECONDS: float = 5.0  # Quick health-check after token set
AUTH_RETRY_MAX_ATTEMPTS: int = 2  # Retry transient auth transport/server errors

AUTH_METHOD_ALIASES: dict[str, str] = {
    "browser": "browser-auth",
    "admin": "browser-auth",
}
SUPPORTED_AUTH_METHODS: tuple[str, ...] = (
    "api-key",
    "browser-auth",
    "sso",
    "google",
    "github",
    "gitlab",
    "email",
    "azureadv2",
)


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
        auth_method: Auth method (e.g. "api-key", "browser-auth", "sso",
            "google", "github", "gitlab", "email"). If None, uses env/default.
        email: Email for auth. Required for ``auth_method="email"``.
        auth_tenant: SSO tenant. Required for ``auth_method="sso"``.

    The client can be used as a context manager (with APIClient(...) as client:).
    When not using ``with``, call close() when done to release connections.

    """

    client: httpx.Client | None  # Set in __init__; set to None in close().

    def __init__(
        self,
        max_retries: int | None = None,
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
        auth_tenant: str | None = None,
        allowed_api_hosts: list[str] | None = None,
    ) -> None:
        super().__init__()
        # Set up logging
        from endorlabs.utils.logging_config import (
            apply_client_session_log_level,
            setup_logging,
        )

        self.logger = setup_logging("endorlabs")
        self.logger.addFilter(
            RedactingFilter(
                [
                    redaction_pattern,
                    (json_redaction_pattern, JSON_REDACTION_REPLACEMENT),
                    (url_token_redaction_pattern, url_token_redaction_replacement),
                ]
            )
        )

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
        if not os.getenv("ENDOR_API"):
            os.environ["ENDOR_API"] = "https://api.endorlabs.com"
        self.base_url: str = (
            base_url or os.getenv("ENDOR_API") or "https://api.endorlabs.com"
        )
        self._allowed_api_hosts = self._build_allowed_api_hosts(allowed_api_hosts)

        # Get token if provided directly
        self._provided_token = token or os.getenv("ENDOR_TOKEN")
        self._email = email or os.getenv("ENDOR_AUTH_EMAIL")
        self._auth_tenant = (
            auth_tenant
            or os.getenv("ENDOR_AUTH_TENANT")
            or os.getenv("ENDOR_INIT_AUTH_TENANT")
        )

        # Determine interactive auth mode. No undocumented env-mode fallback:
        # - explicit auth_method wins
        # - otherwise a provided token implies browser-auth validation path
        # - otherwise use api-key credentials flow
        normalized_auth_method = "api-key"
        if auth_method:
            normalized_auth_method = self._normalize_auth_method(auth_method)
        elif key is not None or secret is not None:
            # Explicit constructor credentials take precedence over env token.
            normalized_auth_method = "api-key"
        elif token is not None or self._provided_token:
            normalized_auth_method = "browser-auth"
        self.auth_method = normalized_auth_method
        self._validate_auth_method()

        # Browser-family flows validate ENDOR_TOKEN first; if invalid, then
        # interactive browser fallback.
        if self.auth_method != "api-key":
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
                    "APIClient(auth_method='browser-auth')"
                )
                self.logger.error(error_msg)
                raise ValidationError(error_msg)

        # Store browser auth parameters
        self._browser_name = os.getenv("ENDOR_BROWSER")

        # Initialize token expiration tracking
        self._token: str | None = None
        self._token_expires: datetime | None = None
        # Browser auth session flag: once a browser token is validated,
        # avoid proactive reauth on token property reads.
        self._browser_session_validated = False

        # Get max_retries with precedence: explicit parameter > env var > default (5)
        if max_retries is None:
            env_val = os.getenv("ENDOR_MAX_RETRIES")
            max_retries = int(env_val) if env_val else 5

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
        return

    def _rate_limit(self) -> None:
        """Apply a delay if a rate limit was previously encountered."""
        if self.rate_limit_delay > 0:
            wait_time = self.rate_limit_delay - (time.time() - self.last_request_time)
            if wait_time > 0:
                self.logger.warning(
                    "Rate limit encountered. Waiting for %.2f seconds.",
                    wait_time,
                )
                time.sleep(wait_time)
            self.rate_limit_delay = 0

    def _headers_copy(self) -> dict[str, str]:
        """Return a mutable copy of request headers with string values."""
        return dict(self._request_headers)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL: use as-is if absolute, prepend base_url if relative."""
        if url.startswith(("http://", "https://")):
            self._validate_absolute_url_host(url)
            return url
        # Relative URL: prepend base_url with proper slash handling
        base = self.base_url.rstrip("/")
        url = url.lstrip("/")
        return f"{base}/{url}"

    def _build_allowed_api_hosts(self, allowed_api_hosts: list[str] | None) -> set[str]:
        """Build a trusted host allowlist from base_url and optional configuration."""
        hosts: set[str] = set()
        base_host = urlparse(self.base_url).hostname
        if isinstance(base_host, bytes):
            base_host = base_host.decode("utf-8", errors="ignore")
        if base_host:
            hosts.add(base_host.lower())

        env_hosts_raw = os.getenv("ENDOR_ALLOWED_API_HOSTS", "")
        env_hosts = [h.strip() for h in env_hosts_raw.split(",") if h.strip()]

        for host in [*(allowed_api_hosts or []), *env_hosts]:
            normalized = host.lower()
            if normalized:
                hosts.add(normalized)
        return hosts

    def _validate_absolute_url_host(self, absolute_url: str) -> None:
        """Reject absolute URLs pointing to hosts outside the trusted allowlist."""
        parsed = urlparse(absolute_url)
        host = parsed.hostname.lower() if parsed.hostname else None
        if not host:
            raise ValidationError(
                f"Absolute URL '{absolute_url}' is missing a valid host"
            )
        if host not in self._allowed_api_hosts:
            allowed = ", ".join(sorted(self._allowed_api_hosts))
            raise ValidationError(
                f"Absolute URL '{absolute_url}' targets disallowed host '{host}'. "
                f"Allowed hosts: {allowed}"
            )

    def _redact_log_data(self, data: Any) -> str:
        """Redact sensitive data from logging."""
        if data is None:
            return "None"
        data_str = str(data)
        # Apply both single-quote (Python repr) and double-quote (JSON) patterns
        data_str = _REPR_REDACT_RE.sub(r"'\1': '***REDACTED***'", data_str)
        data_str = _JSON_REDACT_RE.sub(JSON_REDACTION_REPLACEMENT, data_str)
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
                    "%s response %s - %s",
                    method,
                    response.status_code,
                    self._truncate_for_logging(response.text),
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
                        "Retryable status %s, retrying in %.1fs (attempt %s/%s)",
                        e.response.status_code,
                        backoff,
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    time.sleep(backoff)
                    continue
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt < self.max_retries:
                    backoff = self.backoff_factor * (2**attempt)
                    self.logger.warning(
                        "Network error, retrying in %.1fs (attempt %s/%s): %s",
                        backoff,
                        attempt + 1,
                        self.max_retries + 1,
                        e,
                    )
                    time.sleep(backoff)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise EndorAPIError("Retry loop exited without response or exception")

    def _handle_rate_limited(self, response: httpx.Response) -> None:
        """Handle HTTP 429 responses by setting rate-limit delay."""
        retry_info = response.headers.get("Retry-After", "no retry info")
        self.logger.warning("Rate limited (429), retrying with backoff.")
        self.logger.debug(
            "Rate limit detail: Retry-After=%s, url=%s",
            retry_info,
            response.url,
        )
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            self.rate_limit_delay = int(retry_after) + 1
        else:
            self.rate_limit_delay = (
                self.rate_limit_delay if self.rate_limit_delay > 0 else 5
            )

    def _handle_unauthorized(
        self,
        response: httpx.Response,
        *,
        method: str | None,
        url: str | None,
        _reauth_attempted: bool,
        **kwargs: Any,
    ) -> httpx.Response | None:
        """Handle HTTP 401 responses with single reauth retry."""
        if _reauth_attempted:
            self.logger.error(
                "Unable to reauthenticate. "
                "Verify credentials are valid and not expired."
            )
            return None
        self.logger.warning(
            "Unable to authenticate (401). Verify credentials are valid."
        )
        self.logger.debug("Authentication detail: url=%s", response.url)
        self.logger.info("Attempting to reauthenticate...")
        new_token = self.authenticate()
        if new_token:
            self._request_headers["Authorization"] = f"Bearer {new_token}"
            self.default_headers = self._headers_copy()
            self.logger.info("Reauthentication completed.")
            if method and url:
                self.logger.info("Retrying %s request to %s", method, url)
                assert self.client is not None, "APIClient is closed"
                retry_response = self.client.request(method=method, url=url, **kwargs)
                return self._handle_response(
                    retry_response,
                    method=method,
                    url=url,
                    _reauth_attempted=True,
                    **kwargs,
                )
        return None

    def _handle_not_implemented(
        self,
        response: httpx.Response,
        *,
        method: str | None,
    ) -> None:
        """Log HTTP 501 details."""
        error_details = self._parse_error_response(response)
        self.logger.error("Operation not supported (501) for %s.", response.url)
        self.logger.debug(
            "501 detail: method=%s, error=%s",
            method or "UNKNOWN",
            error_details,
        )

    def _handle_server_error(
        self,
        response: httpx.Response,
        *,
        status_code: int,
        method: str | None,
    ) -> None:
        """Log retryable server-side errors."""
        error_details = self._parse_error_response(response)
        self.logger.warning("Server error %s, retrying with backoff.", status_code)
        self.logger.debug(
            "Server error detail: method=%s, url=%s, error=%s",
            method or "UNKNOWN",
            response.url,
            error_details,
        )

    def _handle_client_error(
        self,
        response: httpx.Response,
        *,
        status_code: int,
        method: str | None,
    ) -> None:
        """Log non-retryable client-side errors."""
        error_details = self._parse_error_response(response)
        error_type = {
            400: "Validation error",
            403: "Permission denied",
            404: "Resource not found",
            409: "Conflict",
        }.get(status_code, f"Client error {status_code}")
        self.logger.error("%s (%s) for %s.", error_type, status_code, response.url)
        self.logger.debug(
            "Client error detail: method=%s, response=%s",
            method or "UNKNOWN",
            error_details,
        )

    def _handle_response(
        self,
        response: httpx.Response,
        method: str | None = None,
        url: str | None = None,
        *,
        _reauth_attempted: bool = False,
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
                self._handle_rate_limited(response)
                raise

            # Handle authentication failure (401) - single retry after reauth
            if status_code == 401:
                retried = self._handle_unauthorized(
                    response,
                    method=method,
                    url=url,
                    _reauth_attempted=_reauth_attempted,
                    **kwargs,
                )
                if retried is not None:
                    return retried
                raise

            # Handle 501 Not Implemented - non-retryable client error
            # (method/operation not supported, not a transient server error)
            if status_code == 501:
                self._handle_not_implemented(response, method=method)
                raise

            # Handle server errors (5xx) - retryable
            if status_code >= 500:
                self._handle_server_error(
                    response,
                    status_code=status_code,
                    method=method,
                )
                raise

            # Handle client errors (400, 403, 404, 409) - not retried, graceful exit
            if status_code in (400, 403, 404, 409):
                self._handle_client_error(
                    response,
                    status_code=status_code,
                    method=method,
                )
                raise

            # Other HTTP errors
            error_details = self._parse_error_response(response)
            self.logger.debug(
                "API error %s on %s request to %s: %s. Response: %s",
                status_code,
                method or "UNKNOWN",
                response.url,
                e,
                error_details,
            )
            raise

        except httpx.ConnectError as e:
            # Network connection errors - retryable (retry loop in _request_with_retry)
            self.logger.error(
                "Unable to connect to %s after %s retries.",
                url or "unknown URL",
                self.max_retries,
            )
            self.logger.debug(
                "Connect error detail: method=%s, error=%s",
                method or "UNKNOWN",
                e,
            )
            raise

        except httpx.TimeoutException as e:
            # Request timeout errors - retryable (retry loop in _request_with_retry)
            self.logger.error(
                "Request to %s timed out after %s retries.",
                url or "unknown URL",
                self.max_retries,
            )
            self.logger.debug(
                "Timeout detail: method=%s, error=%s",
                method or "UNKNOWN",
                e,
            )
            raise

        except httpx.RequestError as e:
            # Other network-related errors - retryable
            self.logger.error(
                "Unable to complete request to %s after %s retries.",
                url or "unknown URL",
                self.max_retries,
            )
            self.logger.debug(
                "Request error detail: method=%s, error=%s",
                method or "UNKNOWN",
                e,
            )
            raise

    # -- Internal helpers for the public HTTP methods -----------------------

    def _prepare_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Return session headers merged with *extra* (caller headers win)."""
        merged = self._headers_copy()
        if extra:
            merged.update(extra)
        return merged

    def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Shared pipeline: rate-limit, auth, normalize, headers, log, retry."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)

        request_kwargs = kwargs.copy()
        request_kwargs["headers"] = self._prepare_headers(request_kwargs.get("headers"))

        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            "%s request to: %s with params: %s, data: %s, json: %s",
            method,
            normalized_url,
            params,
            log_data,
            log_json,
        )
        return self._request_with_retry(
            method,
            normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    # -- Public HTTP verbs (thin wrappers around _request) -----------------

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """GET request (httpx.Response)."""
        return self._request("GET", url, params=params, data=data, json=json, **kwargs)

    def post(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """POST request (httpx.Response)."""
        return self._request("POST", url, params=params, data=data, json=json, **kwargs)

    def patch(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """PATCH request (httpx.Response)."""
        return self._request(
            "PATCH", url, params=params, data=data, json=json, **kwargs
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
        return self._request("PUT", url, params=params, data=data, json=json, **kwargs)

    def delete(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json: Any | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """DELETE request (httpx.Response)."""
        return self._request(
            "DELETE", url, params=params, data=data, json=json, **kwargs
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
                    "Reached max_pages limit (%s). Stopping pagination after %s pages.",
                    max_pages,
                    page_count,
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
        # Browser auth is session-like: once validated, keep token until a 401
        # path triggers explicit reauthentication.
        if self._auth_type == "browser":
            if self._token is None or not self._browser_session_validated:
                _ = self.authenticate()
            return self._token

        # If no token, authenticate.
        if self._token is None:
            _ = self.authenticate()
        elif self._token_expires is not None:
            # Check if token expires within 30 minutes
            now = datetime.now(UTC)
            time_until_expiry = (self._token_expires - now).total_seconds()
            if time_until_expiry <= TOKEN_REFRESH_THRESHOLD_SECONDS:
                _ = self.authenticate()
        # Unknown-expiry API-key tokens are treated as session-valid until a 401
        # triggers explicit reauthentication in _handle_unauthorized.
        return self._token

    @property
    def is_expired(self) -> bool:
        """Check if the current token is expired or about to expire.

        Returns:
            True if token is expired or expires within
            TOKEN_EXPIRY_CHECK_SECONDS, False otherwise.

        """
        if self._token_expires is None:
            return True
        now = datetime.now(self._token_expires.tzinfo)
        time_until_expiry = (self._token_expires - now).total_seconds()
        return time_until_expiry <= TOKEN_EXPIRY_CHECK_SECONDS

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

    @property
    def auth_type(self) -> Literal["api-key", "browser"]:
        """Return the active authentication mode."""
        return cast("Literal['api-key', 'browser']", self._auth_type)

    @property
    def is_api_key_auth(self) -> bool:
        """True when API key authentication is active."""
        return self._auth_type == "api-key"

    def get_user_info(self) -> dict[str, object] | None:
        """Fetch canonical authenticated user info from ``/v1/auth``.

        Returns:
            Parsed response payload on success, otherwise ``None``.

        """
        try:
            response = self.get(
                "v1/auth",
                headers={"Accept": "application/json"},
            )
            data = response.json()
            if isinstance(data, dict):
                return cast("dict[str, object]", data)
        except (httpx.HTTPError, ValueError, TypeError) as e:
            self.logger.debug("Unable to fetch user info from v1/auth: %s", e)
        return None

    def _authenticate_api_key(self) -> str | None:
        """Authenticate using API key and secret."""
        assert self.client is not None, "APIClient is closed"
        payload = {"key": self.key, "secret": self.secret}
        last_error: Exception | None = None
        for attempt in range(AUTH_RETRY_MAX_ATTEMPTS + 1):
            try:
                response = self.client.post(
                    "v1/auth/api-key",
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                _ = response.raise_for_status()
                data_raw = response.json()
                if not isinstance(data_raw, dict):
                    raise TypeError("Invalid auth response: expected JSON object")
                data = cast("dict[str, Any]", data_raw)
                token_raw = data.get("token")
                if not isinstance(token_raw, str) or not token_raw:
                    raise ValidationError("Invalid auth response: missing token")
                token = token_raw

                self._token_expires = self._parse_token_expiration(data)

                # Store token
                self._token = token

                # Update request headers for subsequent requests
                self._request_headers["Authorization"] = f"Bearer {token}"
                self.default_headers = self._headers_copy()
                return token
            except ValueError:
                # Surface malformed auth responses as explicit startup errors.
                raise
            except httpx.HTTPStatusError as error:
                last_error = error
                status = error.response.status_code
                is_retryable = status >= 500 and attempt < AUTH_RETRY_MAX_ATTEMPTS
                if is_retryable:
                    backoff = self.backoff_factor * (2**attempt)
                    self.logger.warning(
                        "Transient auth HTTP %s, retrying in %.1fs (attempt %s/%s)",
                        status,
                        backoff,
                        attempt + 1,
                        AUTH_RETRY_MAX_ATTEMPTS + 1,
                    )
                    time.sleep(backoff)
                    continue
                break
            except (
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.RequestError,
            ) as error:
                last_error = error
                if attempt < AUTH_RETRY_MAX_ATTEMPTS:
                    backoff = self.backoff_factor * (2**attempt)
                    self.logger.warning(
                        (
                            "Transient auth transport error, retrying in %.1fs "
                            "(attempt %s/%s): %s"
                        ),
                        backoff,
                        attempt + 1,
                        AUTH_RETRY_MAX_ATTEMPTS + 1,
                        error,
                    )
                    time.sleep(backoff)
                    continue
                break

        if last_error is not None:
            self.logger.error("Unable to authenticate with API key: %s", last_error)
        self._token = None
        self._token_expires = None
        return None

    def _parse_token_expiration(self, data: dict[str, Any]) -> datetime | None:
        """Parse token expiration from API auth response payload.

        Supports:
        - absolute timestamp fields: expirationTime / expiration_time
        - ttl fields in seconds: expiresIn / expires_in / ttl / ttl_seconds
        """
        expires_value = data.get("expirationTime")
        if expires_value is None:
            expires_value = data.get("expiration_time")
        if isinstance(expires_value, str) and expires_value:
            try:
                utc_datetime_str = re.sub(r"\s*Z$", "+00:00", expires_value)
                return datetime.fromisoformat(utc_datetime_str)
            except (TypeError, ValueError) as error:
                self.logger.debug(
                    "Could not parse expiration time '%s': %s",
                    expires_value,
                    error,
                )

        ttl_value = (
            data.get("expiresIn")
            or data.get("expires_in")
            or data.get("ttl_seconds")
            or data.get("ttl")
        )
        ttl_seconds: float | None = None
        if isinstance(ttl_value, (int, float)):
            ttl_seconds = float(ttl_value)
        elif isinstance(ttl_value, str):
            match = re.match(r"^\s*(\d+(?:\.\d+)?)\s*s?\s*$", ttl_value)
            if match:
                ttl_seconds = float(match.group(1))
        if ttl_seconds is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=max(0.0, ttl_seconds))

    def _determine_browser_method(
        self, *, allow_direct_token_fallback: bool = False
    ) -> str | None:
        """Determine browser OAuth method."""
        if (
            self._provided_token
            and self._provided_token != "browser"
            and not allow_direct_token_fallback
        ):
            return None  # Direct token provided, no browser method needed
        return self.auth_method

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

        self.logger.info("Starting browser OAuth flow with method: %s", browser_method)
        return get_browser_token(
            timeout=BROWSER_AUTH_TIMEOUT_SECONDS,
            environment=environment,
            browser_name=self._browser_name,
            method=browser_method,
            email=self._email,
            auth_tenant=self._auth_tenant,
        )

    @staticmethod
    def _normalize_auth_method(auth_method: str) -> str:
        """Normalize auth mode aliases into canonical values."""
        cleaned = auth_method.strip().lower()
        return AUTH_METHOD_ALIASES.get(cleaned, cleaned)

    def _validate_auth_method(self) -> None:
        """Validate auth mode and required mode-specific arguments."""
        if self.auth_method not in SUPPORTED_AUTH_METHODS:
            allowed = ", ".join(SUPPORTED_AUTH_METHODS)
            raise ValidationError(
                f"Unsupported auth_method '{self.auth_method}'. "
                f"Supported modes: {allowed}"
            )

        if self.auth_method == "email" and not self._email:
            raise ValidationError(
                "auth_method='email' requires email=... "
                "(or ENDOR_AUTH_EMAIL environment variable)."
            )

        if self.auth_method == "sso" and not self._auth_tenant:
            raise ValidationError(
                "auth_method='sso' requires auth_tenant=... "
                "(or ENDOR_AUTH_TENANT / ENDOR_INIT_AUTH_TENANT)."
            )

        if self.auth_method == "azureadv2":
            raise ValidationError(
                "auth_method='azureadv2' is recognized for parity but is not "
                "implemented in SDK browser OAuth routing yet. "
                "Use 'sso', 'browser-auth', 'google', 'github', 'gitlab', or 'email'."
            )

    def _validate_and_store_token(self, token: str) -> bool:
        """Validate token and store it.

        Returns:
            ``True`` when token validation succeeds and token is stored,
            otherwise ``False``.

        """
        assert self.client is not None, "APIClient is closed"
        # Validate token by making a test request to get expiration info
        # Some endpoints may return token metadata
        try:
            test_response = self.client.get(
                "meta/version",
                headers={"Authorization": f"Bearer {token}"},
                timeout=TOKEN_VALIDATION_TIMEOUT_SECONDS,
            )
            _ = test_response.raise_for_status()

            # Try to extract expiration from response if available
            # (Most endpoints don't return this, but we try)
            try:
                data = test_response.json()
                expires: str | None = None
                if not isinstance(data, dict):
                    expires = None
                else:
                    data_dict = cast("dict[str, Any]", data)
                    raw_expiration = data_dict.get("expirationTime") or data_dict.get(
                        "expiration_time"
                    )
                    if isinstance(raw_expiration, str):
                        expires = raw_expiration

                if expires is not None:
                    try:
                        utc_datetime_str = re.sub(
                            r"\s*Z$",
                            "+00:00",
                            expires,
                        )
                        self._token_expires = datetime.fromisoformat(utc_datetime_str)
                    except (TypeError, ValueError):
                        self._token_expires = None
                else:
                    # For browser tokens, we don't know expiration
                    # Set to None (will be treated as expired when checked)
                    self._token_expires = None
            except (TypeError, ValueError):
                self._token_expires = None
        except httpx.HTTPError as e:
            self.logger.debug("Token validation request unsuccessful: %s", e)
            self._token = None
            self._token_expires = None
            self._browser_session_validated = False
            return False

        # Store token after successful validation
        self._token = token
        # Update request headers for subsequent requests
        self._request_headers["Authorization"] = f"Bearer {token}"
        self.default_headers = self._headers_copy()
        self._browser_session_validated = self._auth_type == "browser"
        self.logger.info("Browser authentication successful")
        return True

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
            token: str | None = None
            fallback_attempted = False
            has_direct_token = bool(
                self._provided_token and self._provided_token != "browser"
            )

            # First, try provided token if present (constructor/env).
            if has_direct_token:
                provided_token = cast("str", self._provided_token)
                self.logger.info("Validating provided token for browser auth")
                if self._validate_and_store_token(provided_token):
                    return provided_token
                self.logger.info("Provided token invalid; attempting browser fallback")
                fallback_attempted = True

            # Fallback (or primary path when no token provided): browser OAuth flow.
            browser_method = self._determine_browser_method(
                allow_direct_token_fallback=fallback_attempted
            )
            if browser_method is not None and (
                not has_direct_token or fallback_attempted
            ):
                environment = self._extract_environment()
                token = self._get_browser_token(browser_method, environment)

            if not token or not self._validate_and_store_token(token):
                self.logger.error(
                    "Unable to authenticate with browser "
                    "or authentication was cancelled"
                )
                self._token = None
                self._token_expires = None
                self._browser_session_validated = False
                return None

            return token
        except ImportError:
            self.logger.error(
                "Browser authentication requires auth_server module. "
                "This should not happen."
            )
            self._token = None
            self._token_expires = None
            self._browser_session_validated = False
            return None
        except (httpx.HTTPError, OSError, RuntimeError, ValueError) as e:
            self.logger.error("Unable to authenticate with browser: %s", e)
            self._token = None
            self._token_expires = None
            self._browser_session_validated = False
            return None
