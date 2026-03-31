"""Browser-based OAuth authentication server for Endor Labs.

This module provides browser-based OAuth authentication by starting a local
HTTP server to capture the bearer token from the OAuth redirect callback.

⚠️  WARNING: Browser authentication requires human interaction and cannot be
used in CI/CD environments. Use API key authentication (ENDOR_API_CREDENTIALS_KEY
and ENDOR_API_CREDENTIALS_SECRET) for automated environments.
"""

import contextlib
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, override
from urllib.parse import parse_qs, urlparse
from webbrowser import get as get_browser

from .utils.redaction import (
    JSON_REDACTION_REPLACEMENT,
    RedactingFilter,
    json_redaction_pattern,
    redaction_pattern,
    url_token_redaction_pattern,
    url_token_redaction_replacement,
)

logger = logging.getLogger(__name__)
logger.addFilter(
    RedactingFilter(
        [
            redaction_pattern,
            (json_redaction_pattern, JSON_REDACTION_REPLACEMENT),
            (url_token_redaction_pattern, url_token_redaction_replacement),
        ]
    )
)

# Module-level storage for the captured token (lowercase to allow reassignment)
_captured_token: str | None = None

# Default environment
DEFAULT_ENV = "endorlabs.com"

# Authentication method URLs
AUTH_METHODS = {
    "browser-auth": "https://api.{environment}/v1/auth/sso?tenant=endor-admin",
    "sso": "https://api.{environment}/v1/auth/sso?tenant={tenant}",
    "admin": "https://api.{environment}/v1/auth/sso?tenant=endor-admin",
    "google": "https://api.{environment}/v1/auth/google",
    "github": "https://api.{environment}/v1/auth/github",
    "gitlab": "https://api.{environment}/v1/auth/gitlab",
    "email": "https://api.{environment}/v1/auth/login",
}


class TokenHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback that captures the bearer token."""

    def do_GET(self) -> None:
        """Handle GET request from OAuth redirect."""
        global _captured_token
        try:
            # Ignore favicon requests
            if self.path == "/favicon.ico":
                self.send_response(404)
                self.end_headers()
                return

            parsed_url = urlparse(self.path)
            if not parsed_url.query:
                logger.warning("No query parameters in redirect: %s", self.path)
                self.send_response(404)
                self.end_headers()
                return

            params = parse_qs(parsed_url.query, keep_blank_values=False)
            tokens = params.get("token", [])
            if len(tokens) == 1 and tokens[0]:
                _captured_token = tokens[0]
                logger.info("Token captured successfully")
                # Return simple HTML page instead of redirect to prevent new tabs
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                with contextlib.suppress(Exception):
                    redirect_url = f"https://app.{DEFAULT_ENV}"
                    _ = self.wfile.write(
                        b"<html><head><title>Authentication Successful</title>"
                        b"<meta http-equiv='refresh' content='1;url="
                        + redirect_url.encode()
                        + b"'></head>"
                        b"<body><h1>Authentication successful!</h1>"
                        b"<p>Redirecting to Endor Labs...</p></body></html>"
                    )
            else:
                logger.warning("Token not found in redirect: %s", self.path)
                # Redirect to success page only if token not found
                self.send_response(302)
                self.send_header(
                    "Location", f"https://app.{DEFAULT_ENV}/endorctl-success"
                )
                self.end_headers()
            self.close_connection = True
        except Exception as e:
            logger.error("Error handling OAuth callback: %s", e)
            self.send_response(500)
            self.end_headers()
            self.close_connection = True

    def do_POST(self) -> None:
        """Handle POST request from OAuth redirect (SSO may use POST)."""
        # SSO auth may come back with POST, but we handle it the same as GET
        self.do_GET()

    @override
    def log_message(self, format: str, *args: Any, **_kwargs: Any) -> None:
        """Suppress default HTTP server logs."""
        # Optionally enable in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("HTTP Server: %s", format % args)


def get_token(
    timeout: int = 20,
    environment: str = DEFAULT_ENV,
    browser_name: str | None = None,
    method: str = "admin",
    email: str | None = None,
    auth_tenant: str | None = None,
) -> str | None:
    """Get bearer token via browser OAuth flow.

    Starts a local HTTP server on localhost:30000, opens a browser to the
    OAuth URL, and captures the token from the redirect callback.

    ⚠️  WARNING: This function requires human interaction (opens browser window)
    and cannot be used in CI/CD environments. Use API key authentication instead.

    Args:
        timeout: Server timeout in seconds (default: 20)
        environment: API environment domain (default: "endorlabs.com")
        browser_name: Browser name for webbrowser.get() (optional)
        method: Auth method - 'browser-auth', 'sso', 'google', 'github',
            'gitlab', or 'email'. Legacy aliases: 'browser', 'admin'.
        email: Email address for email-based authentication (required if method='email')
        auth_tenant: Tenant name required if method='sso'.

    Returns:
        Bearer token string or None if authentication failed or timed out

    Raises:
        ValueError: If method is not supported, email is required but not provided,
            or if called in a CI/CD environment

    """
    global _captured_token
    _captured_token = None

    # Detect CI/CD environments and prevent browser auth
    ci_indicators = [
        "CI",  # Generic CI flag (GitHub Actions, GitLab CI, etc.)
        "CONTINUOUS_INTEGRATION",  # Travis CI
        "GITHUB_ACTIONS",  # GitHub Actions
        "GITLAB_CI",  # GitLab CI
        "JENKINS_URL",  # Jenkins
        "BUILDKITE",  # Buildkite
        "CIRCLECI",  # CircleCI
    ]
    is_ci = any(os.getenv(indicator) for indicator in ci_indicators)

    if is_ci:
        raise ValueError(
            "Browser authentication cannot be used in CI/CD environments. "
            "Browser authentication requires human interaction (opens browser window). "
            "Use API key authentication instead by setting ENDOR_API_CREDENTIALS_KEY "
            "and ENDOR_API_CREDENTIALS_SECRET environment variables."
        )

    normalized_method = {"browser": "browser-auth", "admin": "browser-auth"}.get(
        method, method
    )

    if normalized_method not in AUTH_METHODS:
        raise ValueError(
            f"Unsupported auth method: {normalized_method}. "
            f"Supported methods: {', '.join(AUTH_METHODS.keys())}"
        )

    if normalized_method == "email" and not email:
        raise ValueError("Email address required for email-based authentication")

    if normalized_method == "sso" and not auth_tenant:
        raise ValueError("Tenant is required for sso authentication")

    # Build OAuth URL
    auth_url_template = AUTH_METHODS[normalized_method]
    auth_url = auth_url_template.format(
        environment=environment,
        tenant=auth_tenant or "endor-admin",
    )

    # Add email parameter for email auth
    if normalized_method == "email":
        auth_url = f"{auth_url}?email={email}"

    # Add redirect parameter
    redirect_param = "&" if "?" in auth_url else "?"
    auth_url = f"{auth_url}{redirect_param}redirect=cli"

    try:
        # Start local HTTP server
        server = HTTPServer(("localhost", 30000), TokenHandler)
        server.timeout = timeout

        # Open browser (only once)
        browser = get_browser(browser_name)
        logger.info("Opening browser for %s authentication...", normalized_method)
        _ = browser.open_new_tab(auth_url)

        # Wait for callback (blocks until request received or timeout)
        logger.info(
            "Waiting for OAuth callback on localhost:30000 (timeout: %ss)...",
            timeout,
        )

        # Handle request - this will block until ONE request is received
        # or timeout. After handling one request, server stops listening
        # (handle_request only processes one)
        _ = server.handle_request()

        # Clean up server
        server.server_close()

        if _captured_token:
            logger.info("Browser authentication successful")
            return _captured_token
        else:
            logger.warning("No token received from OAuth callback")
            return None

    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(
                "Port 30000 is already in use. "
                "Please close any other applications using this port."
            )
        else:
            logger.error("Unable to start OAuth server: %s", e)
        return None
    except Exception as e:
        logger.error("Unable to complete browser authentication: %s", e)
        return None
