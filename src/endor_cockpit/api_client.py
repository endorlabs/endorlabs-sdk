"""
Description:
    API Client to provide REST calls with retry, rate limiting, pagination,
    and logging with redaction.

Author:
    tgowan@endor.ai
"""

import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ENDOR_NAMESPACE = os.getenv("ENDOR_NAMESPACE")
# TODO: Determine if needed or as an init param or env var

# Logger redaction definitions
REDACTED_KEYS = ["authorization", "secret", "token", "key"]
redaction_pattern = (
    r"'(" + "|".join(REDACTED_KEYS) + r")':\s*'.*?'"
)  # Regex pattern to redact keys and their values


class RedactingFilter(logging.Filter):
    def __init__(self, patterns):
        super().__init__()
        self._patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def filter(self, record):
        record.msg = self._redact(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: self._redact(v) for k, v in record.args.items()}
        return True

    def _redact(self, message):
        if not isinstance(message, str):
            message = str(message)
        for pattern in self._patterns:
            message = pattern.sub(r"'\1': '***REDACTED***'", message)
        return message


class APIClient:
    """Simple API client with retry, rate limiting handling and redacted logging.

    Args:
        max_retries: Maximum number of retries for requests.
        backoff_factor: Backoff factor for retries.
        status_forcelist: HTTP status codes that trigger a retry.
        logging_level: Logging level for the client's logger.
    """

    @staticmethod
    def _load_endorctl_config() -> Optional[Dict[str, str]]:
        """
        Load configuration from endorctl config.yaml file.

        Checks multiple locations in order:
        1. Project root .endorctl/config.yaml (for local development)
        2. ~/.endorctl/config.yaml (or C:\\Users\\<user>\\.endorctl\\config.yaml
           on Windows) for user-wide configuration

        Returns:
            Dictionary with config values or None if file doesn't exist
        """
        config_paths = []

        # Check project root first (for local development)
        try:
            # Try to find project root by looking for pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                pyproject = current / "pyproject.toml"
                if pyproject.exists():
                    project_config = current / ".endorctl" / "config.yaml"
                    if project_config.exists():
                        config_paths.append(project_config)
                    break
                current = current.parent
        except Exception:
            pass

        # Check user home directory
        home = Path.home()
        user_config = home / ".endorctl" / "config.yaml"
        if user_config.exists():
            config_paths.append(user_config)

        # Try each config path in order
        for config_path in config_paths:
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    if not isinstance(config, dict):
                        continue
                    # Convert to string values and filter for relevant keys
                    result = {}
                    for key in [
                        "ENDOR_API",
                        "ENDOR_API_CREDENTIALS_KEY",
                        "ENDOR_API_CREDENTIALS_SECRET",
                        "ENDOR_NAMESPACE",
                        "ENDOR_TOKEN",
                        "ENDOR_AUTH_METHOD",
                        "ENDOR_BROWSER",
                    ]:
                        if key in config:
                            result[key] = str(config[key])
                    if result:
                        return result
            except Exception:
                # Silently fail - config file may be malformed
                continue

        return None

    def __init__(
        self,
        max_retries: int = 15,
        backoff_factor: float = 0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        logging_level: str = "INFO",
        token: Optional[str] = None,
        auth_method: Optional[str] = None,
        email: Optional[str] = None,
    ):
        # Set up logging
        from endor_cockpit.utils.logging_config import setup_logging

        self.logger = setup_logging("endor_cockpit")
        self.logger.addFilter(RedactingFilter([redaction_pattern]))

        # Load config from endorctl config.yaml as fallback
        config_file = self._load_endorctl_config()

        # Initialize API client parameters
        # Precedence: parameters > environment variables > config file > defaults
        self.base_url = (
            os.getenv("ENDOR_API")
            or (config_file.get("ENDOR_API") if config_file else None)
            or "https://api.endorlabs.com"
        )

        # Determine authentication method
        # Precedence: parameter > env var > config file > default (api-key)
        self.auth_method = (
            auth_method
            or os.getenv("ENDOR_AUTH_METHOD")
            or (config_file.get("ENDOR_AUTH_METHOD") if config_file else None)
            or "api-key"
        )

        # Get token if provided directly
        self._provided_token = (
            token
            or os.getenv("ENDOR_TOKEN")
            or (config_file.get("ENDOR_TOKEN") if config_file else None)
        )

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
            # API key authentication (default)
            self.key = os.getenv("ENDOR_API_CREDENTIALS_KEY") or (
                config_file.get("ENDOR_API_CREDENTIALS_KEY") if config_file else None
            )
            self.secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET") or (
                config_file.get("ENDOR_API_CREDENTIALS_SECRET") if config_file else None
            )
            self._auth_type = "api-key"

            if not self.key or not self.secret:
                error_msg = (
                    "API credentials not found. Please provide credentials via:\n"
                    "  - Environment variables: ENDOR_API_CREDENTIALS_KEY and "
                    "ENDOR_API_CREDENTIALS_SECRET\n"
                    "  - endorctl config file: ~/.endorctl/config.yaml "
                    "(or C:\\Users\\<user>\\.endorctl\\config.yaml on Windows)\n"
                    "  - Or use browser authentication: APIClient(auth_method='browser')"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # Store browser auth parameters
        self._browser_name = (
            os.getenv("ENDOR_BROWSER")
            or (config_file.get("ENDOR_BROWSER") if config_file else None)
        )
        self._email = email

        # Initialize token expiration tracking
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

        # Initialize session with retries
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=None,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.rate_limit_delay = 0
        self.last_request_time = 0
        self.logger_len = 25

        # Authenticate and set initial headers
        # Use token property to ensure fresh token with expiration tracking
        _ = self.token
        if self._token:
            self.session.headers.update({"Authorization": f"Bearer {self._token}"})
        self.default_headers = self.session.headers.copy()

    def _rate_limit(self):
        """Applies a delay if a rate limit was previously encountered."""
        if self.rate_limit_delay > 0:
            wait_time = self.rate_limit_delay - (time.time() - self.last_request_time)
            if wait_time > 0:
                self.logger.warning(
                    f"Rate limit encountered. Waiting for {wait_time:.2f} seconds."
                )
                time.sleep(wait_time)
            self.rate_limit_delay = 0

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

    def _ensure_authenticated(self):
        """
        Ensure token is fresh and session headers are updated.

        This method should be called before making API requests to ensure
        the token is valid and headers are up to date.
        """
        # Access token property to trigger refresh if needed
        current_token = self.token
        if current_token:
            # Update session headers with current token
            self.session.headers.update({"Authorization": f"Bearer {current_token}"})

    def _handle_response(
        self,
        response: requests.Response,
        method: str = None,
        url: str = None,
        **kwargs,
    ) -> Any:
        self.last_request_time = time.time()
        try:
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_info = response.headers.get("Retry-After", "no retry info")
                self.logger.warning(
                    f"Rate limit encountered (429): {retry_info}. "
                    f"Request to {response.url} was throttled."
                )
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    self.rate_limit_delay = int(retry_after) + 1
                else:
                    self.rate_limit_delay = (
                        self.rate_limit_delay if self.rate_limit_delay > 0 else 5
                    )
                raise
            if response.status_code == 401:
                self.logger.warning(
                    f"Authentication failed (401): Invalid or expired credentials. "
                    f"Request to {response.url} was unauthorized."
                )
                self.logger.info("Attempting to reauthenticate...")
                # Use authenticate() which will use the appropriate auth method
                new_token = self.authenticate()
                if new_token:
                    self.session.headers.update(
                        {"Authorization": f"Bearer {new_token}"}
                    )
                    self.default_headers = self.session.headers.copy()
                    self.logger.info("Reauthentication completed.")
                    # Retry the original request
                    if method and url:
                        self.logger.info(f"Retrying {method} request to {url}")
                        retry_response = self.session.request(
                            method=method, url=url, **kwargs
                        )
                        return self._handle_response(
                            retry_response, method=method, url=url, **kwargs
                        )
                raise
            else:
                self.logger.error(
                    f"API error {response.status_code}: {e}. "
                    f"Request to {response.url} failed. "
                    f"Response: {response.text[:200]}..."
                )
                raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request exception: {e}")
            raise

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> requests.Response:
        """GET request compatible with requests library signature."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        # Merge headers if provided
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            # Merge with session headers
            merged_headers = self.session.headers.copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self.session.headers.copy()

        # Log with redaction
        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"GET request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        response = self.session.request(
            method="GET",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )
        self.logger.debug(
            f"GET response: {response.status_code} - {response.text[:200]}..."
        )
        return self._handle_response(
            response,
            method="GET",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def post(
        self,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> requests.Response:
        """POST request compatible with requests library signature."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        # Merge headers if provided
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            # Merge with session headers
            merged_headers = self.session.headers.copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self.session.headers.copy()

        # Log with redaction
        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"POST request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        response = self.session.request(
            method="POST",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )
        self.logger.debug(
            f"POST response: {response.status_code} - {response.text[:200]}..."
        )
        return self._handle_response(
            response,
            method="POST",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def patch(
        self,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> requests.Response:
        """PATCH request compatible with requests library signature."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        # Merge headers if provided
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            # Merge with session headers
            merged_headers = self.session.headers.copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self.session.headers.copy()

        # Log with redaction
        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"PATCH request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        response = self.session.request(
            method="PATCH",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )
        self.logger.debug(
            f"PATCH response: {response.status_code} - {response.text[:200]}..."
        )
        return self._handle_response(
            response,
            method="PATCH",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def put(
        self,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> requests.Response:
        """PUT request compatible with requests library signature."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        # Merge headers if provided
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            # Merge with session headers
            merged_headers = self.session.headers.copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self.session.headers.copy()

        # Log with redaction
        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"PUT request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        response = self.session.request(
            method="PUT",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )
        self.logger.debug(
            f"PUT response: {response.status_code} - {response.text[:200]}..."
        )
        return self._handle_response(
            response,
            method="PUT",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def delete(
        self,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        **kwargs,
    ) -> requests.Response:
        """DELETE request compatible with requests library signature."""
        self._rate_limit()
        self._ensure_authenticated()
        normalized_url = self._normalize_url(url)
        # Merge headers if provided
        request_kwargs = kwargs.copy()
        if "headers" in request_kwargs:
            # Merge with session headers
            merged_headers = self.session.headers.copy()
            merged_headers.update(request_kwargs["headers"])
            request_kwargs["headers"] = merged_headers
        else:
            request_kwargs["headers"] = self.session.headers.copy()

        # Log with redaction
        log_data = self._redact_log_data(data) if data else None
        log_json = self._redact_log_data(json) if json else None
        self.logger.debug(
            f"DELETE request to: {normalized_url} with params: {params}, "
            f"data: {log_data}, json: {log_json}"
        )
        response = self.session.request(
            method="DELETE",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )
        self.logger.debug(
            f"DELETE response: {response.status_code} - {response.text[:200]}..."
        )
        return self._handle_response(
            response,
            method="DELETE",
            url=normalized_url,
            params=params,
            data=data,
            json=json,
            **request_kwargs,
        )

    def _extract_items_from_response(self, response_data: Any) -> List[Any]:
        """Extract items from paginated response."""
        if isinstance(response_data, dict) and "list" in response_data:
            list_data = response_data["list"]
            if isinstance(list_data, dict) and "objects" in list_data:
                return list_data["objects"]
        elif isinstance(response_data, list):
            return response_data
        return []

    def _extract_next_page_token(self, response_data: Any) -> Optional[str]:
        """Extract next page token from paginated response."""
        if isinstance(response_data, dict) and "list" in response_data:
            list_data = response_data["list"]
            if isinstance(list_data, dict) and "response" in list_data:
                response_meta = list_data["response"]
                if isinstance(response_meta, dict):
                    return response_meta.get("next_page_token")
        return None

    def get_all(
        self,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        max_pages: Optional[int] = None,
        **kwargs,
    ) -> Iterator[Dict[str, Any]]:
        """
        Get all items from a paginated endpoint, automatically handling
        page_token pagination.

        Yields individual items from paginated responses. Handles Endor Labs
        pagination format with list.objects and next_page_token.

        Args:
            url: Endpoint URL (relative or absolute)
            params: Query parameters (will be updated with page_token)
            data: Request body data
            json: Request body JSON
            max_pages: Optional maximum number of pages to fetch.
                If None, fetches all pages.
            **kwargs: Additional arguments passed to request

        Yields:
            Individual items from paginated responses
        """
        normalized_url = self._normalize_url(url)
        page_token = None
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

            # Update params with page_token if present
            if page_token is not None:
                request_params["list_parameters.page_token"] = str(page_token)
            elif "list_parameters.page_token" in request_params:
                # Remove page_token if we're starting fresh
                del request_params["list_parameters.page_token"]

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
            for item in items:
                yield item

            page_count += 1

            # Check for next page token
            page_token = self._extract_next_page_token(response_data)

            # Break if no more pages
            if not page_token:
                break

        self.logger.debug(
            f"Fetched all items from {normalized_url} across {page_count} pages"
        )

    @property
    def token(self) -> Optional[str]:
        """
        Get current token, automatically refreshing if expired or about to expire.

        Returns:
            Current bearer token string, or None if authentication fails.
        """
        # If no token or token expires within 30 minutes, re-authenticate
        if self._token is None or self._token_expires is None:
            self.authenticate()
        else:
            # Check if token expires within 30 minutes
            now = datetime.now(timezone.utc)
            time_until_expiry = (self._token_expires - now).total_seconds()
            if time_until_expiry <= 30 * 60:  # 30 minutes in seconds
                self.authenticate()
        return self._token

    @property
    def is_expired(self) -> bool:
        """
        Check if the current token is expired or about to expire.

        Returns:
            True if token is expired or expires within 60 seconds, False otherwise.
        """
        if self._token_expires is None:
            return True
        # Check if token expires within 60 seconds
        now = datetime.now(self._token_expires.tzinfo)
        time_until_expiry = (self._token_expires - now).total_seconds()
        return time_until_expiry <= 60

    def authenticate(self) -> Optional[str]:
        """
        Authenticate and update session headers with bearer token.

        Supports both API key and browser-based OAuth authentication.

        Returns:
            Bearer token string or None if authentication fails.
        """
        if self._auth_type == "browser":
            return self._authenticate_browser()
        else:
            return self._authenticate_api_key()

    def _authenticate_api_key(self) -> Optional[str]:
        """Authenticate using API key and secret."""
        try:
            payload = {"key": self.key, "secret": self.secret}
            response = requests.post(
                f"{self.base_url}/v1/auth/api-key",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
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

            # Store token and update environment
            self._token = token
            os.environ["ENDOR_TOKEN"] = token

            # Update session headers
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.default_headers = self.session.headers.copy()
            return token
        except Exception as e:
            self.logger.error(f"Unable to authenticate with API key: {e}")
            self._token = None
            self._token_expires = None
            return None

    def _authenticate_browser(self) -> Optional[str]:
        """
        Authenticate using browser-based OAuth flow.

        ⚠️  WARNING: This method requires human interaction and cannot be used
        in CI/CD environments. It opens a browser window and waits for user
        authentication. Use API key authentication (ENDOR_API_CREDENTIALS_KEY
        and ENDOR_API_CREDENTIALS_SECRET) for automated environments.

        Returns:
            Bearer token string or None if authentication fails.
        """
        try:
            from endor_cockpit.auth_server import get_token as get_browser_token

            # Determine auth method for browser OAuth
            if self._provided_token and self._provided_token != "browser":
                # Direct token provided, validate it
                token = self._provided_token
                self.logger.info("Using provided token for authentication")
            else:
                # Trigger browser OAuth flow
                # Map auth_method to browser OAuth method
                browser_method = self.auth_method
                if browser_method == "browser":
                    browser_method = "admin"  # Default to admin SSO

                # Extract environment from base_url
                environment = self.base_url.replace("https://api.", "").replace(
                    "http://api.", ""
                )
                if environment == self.base_url:
                    # No api. prefix, use default
                    environment = "endorlabs.com"

                self.logger.info(
                    f"Starting browser OAuth flow with method: {browser_method}"
                )
                token = get_browser_token(
                    timeout=20,
                    environment=environment,
                    browser_name=self._browser_name,
                    method=browser_method,
                    email=self._email,
                )

            if not token:
                self.logger.error("Browser authentication failed or was cancelled")
                self._token = None
                self._token_expires = None
                return None

            # Validate token by making a test request to get expiration info
            # Some endpoints may return token metadata
            try:
                test_response = requests.get(
                    f"{self.base_url}/meta/version",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5,
                )
                test_response.raise_for_status()

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
                            self._token_expires = datetime.fromisoformat(
                                utc_datetime_str
                            )
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

            # Store token and update environment
            self._token = token
            os.environ["ENDOR_TOKEN"] = token

            # Update session headers
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.default_headers = self.session.headers.copy()
            self.logger.info("Browser authentication successful")
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
