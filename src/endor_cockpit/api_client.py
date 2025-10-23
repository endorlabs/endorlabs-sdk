"""
Description:
    API Client to provide REST calls with retry, rate limiting, pagination,
    and logging with redaction. Also retrieves Swagger JSON from a stable
    endpoint and can execute endorctl commands.

Author:
    tgowan@endor.ai
"""

import json
import logging
import os
import re
import subprocess
import time
from typing import Any, Dict, Optional

import requests
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

    def __init__(
        self,
        max_retries: int = 15,
        backoff_factor: float = 0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        logging_level: str = "INFO",
    ):
        # Set up logging
        from endor_cockpit.utils.logging_config import setup_logging

        self.logger = setup_logging("endor_cockpit")
        self.logger.addFilter(RedactingFilter([redaction_pattern]))

        # Initialize API client parameters
        self.base_url = os.getenv("ENDOR_API") or "https://api.endorlabs.com"
        self.key = os.getenv("ENDOR_API_CREDENTIALS_KEY")
        self.secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET")
        if not self.key or not self.secret:
            error_msg = (
                "API credentials not found in environment variables, "
                "provide ENDOR_API_CREDENTIALS_KEY and/or "
                "ENDOR_API_CREDENTIALS_SECRET as environment variables."
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg)

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

        # Set initial headers
        self.token = self.authenticate()
        self.default_headers = {"Authorization": f"Bearer {self.token}"}

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

    def _handle_response(self, response: requests.Response) -> Any:
        self.last_request_time = time.time()
        try:
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_info = response.headers.get("Retry-After", "no retry info")
                self.logger.warning(
                    f"Rate limit encountered: {response.status_code} - {retry_info}"
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
                self.logger.warning(f"Permissions Error: {response.status_code}")
                self.logger.info("Reauthenticating...")
                self.headers = {"Authorization": f"Bearer {self.authenticate()}"}
                self.logger.info("Reauthenticated.")

            else:
                self.logger.error(f"API error: {response.status_code} - {e}")
                self.logger.error(f"Response content: {response.text}")
                raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request exception: {e}")
            raise

    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ) -> Any:
        self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(f"GET request to: {url} with params: {params}")
        response = self.session.get(url, params=params, headers=headers)
        self.logger.debug(f"GET response: {response.status_code} - {response.text}...")
        return self._handle_response(response)

    def post(self, endpoint, data=None, params=None, headers=None):
        self.logger.debug(
            f"POST request to: {endpoint} with params: {params}, data: {data}"
        )

        self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(f"POST request to: {url} with params: {params}, data: {data}")
        response = self.session.post(url, params=params, json=data, headers=headers)
        self.logger.debug(f"POST response: {response.status_code} - {response.text}...")

        return self._handle_response(response)

    def patch(self, endpoint, data=None, params=None, headers=None):
        self.logger.debug(
            f"PATCH request to: {endpoint} with params: {params}, data: {data}"
        )
        self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(
            f"PATCH request to: {url} with params: {params}, data: {data}"
        )
        response = self.session.patch(url, params=params, json=data, headers=headers)
        self.logger.debug(
            f"PATCH response: {response.status_code} - {response.text}..."
        )
        return self._handle_response(response)

    def put(self, endpoint, data=None, params=None, headers=None):
        self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(f"PUT request to: {url} with data: {data}")
        response = self.session.put(url, json=data, params=params, headers=headers)
        self.logger.debug(f"PUT response: {response.status_code} - {response.text}...")
        return self._handle_response(response)

    def delete(self, endpoint, params=None, headers=None):
        self._rate_limit()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(f"DELETE request to: {url}")
        response = self.session.delete(url, params=params, headers=headers)
        self.logger.debug(
            f"DELETE response: {response.status_code} - {response.text}..."
        )
        return self._handle_response(response)

    def paginate(  # noqa: C901
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        pagination_key: str = "next",
        data_key: Optional[str] = None,
        max_pages: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Handles pagination for GET requests.

        Args:
            endpoint: The API endpoint to paginate.
            params: Initial query parameters.
            pagination_key: The key in the response that contains the URL or token
                           for the next page. Set to None if pagination is handled
                           differently (e.g., by page number).
            data_key: An optional key to extract the list of items from each
                     page's response.
            max_pages: The maximum number of pages to retrieve. If None, it will
                      continue until no next page is indicated.
            **kwargs: Additional keyword arguments to pass to the self.get() method.

        Yields:
            Individual items if data_key is provided, otherwise the entire
            response for each page.
        """
        current_params = params.copy() if params else {}
        page_count = 0
        next_page_url = f"{self.base_url}/{endpoint.lstrip('/')}"

        while max_pages is None or page_count < max_pages:
            # If next_page_url is a full URL, strip the base_url to pass to self.get
            endpoint_to_call = (
                next_page_url.replace(f"{self.base_url}/", "")
                if next_page_url
                else endpoint
            )
            response = self.get(
                endpoint=endpoint_to_call, params=current_params, **kwargs
            )
            page_count += 1

            if data_key:
                # response may be a requests.Response object; try to access json safely
                try:
                    resp_json = response.json()
                except Exception:
                    resp_json = response if isinstance(response, dict) else {}

                items = resp_json.get(data_key) if isinstance(resp_json, dict) else None
                if items:
                    yield from items
                else:
                    self.logger.warning(
                        f"Data key '{data_key}' not found in response "
                        f"for {next_page_url}"
                    )
                    break  # Or handle differently
            else:
                yield response

            if pagination_key:
                # Try parsing next link from JSON body
                try:
                    resp_json = response.json()
                except Exception:
                    resp_json = response if isinstance(response, dict) else {}

                next_link = (
                    resp_json.get(pagination_key)
                    if isinstance(resp_json, dict)
                    else None
                )
                if next_link:
                    if next_link.startswith("http"):
                        next_page_url = next_link
                    else:
                        next_page_url = f"{self.base_url}/{next_link.lstrip('/')}"
                else:
                    break
            else:
                # If no pagination_key, assume pagination is handled by a parameter
                # You might need to adjust the parameter name based on the API
                if "page" in current_params:
                    current_params["page"] += 1
                else:
                    # Start from page 2 if 'page' not initially present
                    current_params["page"] = 2

                # You'll need a condition to determine when to stop if no 'next' link
                # This might involve checking if the current page returns an empty
                # dataset
                if not response.get(data_key):  # Example stop condition
                    break
                # Keep the base URL
                next_page_url = f"{self.base_url}/{endpoint.lstrip('/')}"

    def authenticate(self):
        try:
            payload = {"key": self.key, "secret": self.secret}
            response = requests.post(
                f"{self.base_url}/v1/auth/api-key",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            token = response.json()["token"]
            os.environ["ENDOR_TOKEN"] = token
            return token
        except Exception as e:
            self.logger.error(f"Unable to authenticate: {e}")
            return None

    def get_openapi_spec(
        self, url: Optional[str], path: Optional[str]
    ) -> Dict[str, Any]:
        """
        Retrieves and returns the API Spec JSON from the given URL.

        Args:
            url: Optional URL to fetch the OpenAPI spec from. If None, uses
                 default Endor Labs URL
            path: Optional file path to save the spec to. Will create
                  directories if they don't exist

        Returns:
            Dict containing the OpenAPI specification
        """
        try:
            if url is None:
                url = "/download/openapiv2.swagger.json"

            response = self.get(url, headers={"Accept": "application/json"})
            response_data = response.json()  # Parse JSON from response

            if path is not None:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

                with open(path, "w") as f:
                    json.dump(response_data, f, indent=4)

            return response_data

        except Exception as e:
            self.logger.error(f"Unable to retrieve Swagger JSON from {url}: {e}")
            raise  # Re-raise to let caller handle the error

    # TODO: def get_sitemap_xml() # https://docs.endorlabs.com/sitemap.xml

    def endorctl(self, command: str) -> str:
        """Executes an endorctl command and returns its output."""
        try:
            # Force utf-8 decoding and replace errors to avoid crashes
            # from unexpected bytes
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return (result.stdout or "").strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Command '{command}' failed with error: {e.stderr.strip()}"
            )
            raise
