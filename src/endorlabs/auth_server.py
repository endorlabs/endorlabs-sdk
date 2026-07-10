"""Browser-based OAuth authentication server for Endor Labs.

This module provides browser-based OAuth authentication by starting a local
HTTP server to capture the bearer token from the OAuth redirect callback.

Aligned with endorctl ``browserauth``:

- ``sso`` requires ``auth_tenant`` (no silent ``endor-admin`` default).
- ``browser-auth`` opens a local ``/auth-selector`` page (provider picker).
- Provider modes open ``/v1/auth/{mode}?redirect=cli`` directly.

⚠️  WARNING: Browser authentication requires human interaction and cannot be
used in CI/CD environments. Use API key authentication (ENDOR_API_CREDENTIALS_KEY
and ENDOR_API_CREDENTIALS_SECRET) for automated environments.
"""

from __future__ import annotations

import contextlib
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, cast, override
from urllib.parse import parse_qs, urlencode, urlparse, urlsplit, urlunsplit
from webbrowser import get as get_browser

from endorlabs.core.exceptions import ValidationError
from endorlabs.core.whoami import identity_from_auth_payload
from endorlabs.utils.bearer_token import (
    expiration_from_auth_payload,
    format_expiration_utc,
    format_ttl_label,
)
from endorlabs.utils.logging_config import get_resource_logger

from .utils.redaction import (
    JSON_REDACTION_REPLACEMENT,
    RedactingFilter,
    json_redaction_pattern,
    redaction_pattern,
    url_token_redaction_pattern,
    url_token_redaction_replacement,
)

logger = get_resource_logger(__name__)
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

# OAuth callback port range (aligned with endorctl CLI convention)
OAUTH_CALLBACK_PORT_START = 30000
OAUTH_CALLBACK_PORT_COUNT = 10

# Direct API auth URLs (endorctl getAuthURL parity). ``browser-auth`` is local-only.
AUTH_METHODS = {
    "sso": "https://api.{environment}/v1/auth/sso?tenant={tenant}",
    "google": "https://api.{environment}/v1/auth/google",
    "github": "https://api.{environment}/v1/auth/github",
    "gitlab": "https://api.{environment}/v1/auth/gitlab",
    "azureadv2": "https://api.{environment}/v1/auth/azureadv2",
    "email": "https://api.{environment}/v1/auth/login",
}

_METHOD_ALIASES: dict[str, str] = {
    "browser": "browser-auth",
    "admin": "browser-auth",
}

# HTML template; long attribute lines are intentional (noqa on block via per-line).
_AUTH_SELECTOR_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Select Authentication Method</title>
  <style>
    body {{
      font-family: system-ui, sans-serif; background: #0a0a0a; color: #fff;
      min-height: 100vh; display: flex; align-items: center;
      justify-content: center;
    }}
    .box {{
      background: #1a1a1a; border-radius: 12px; padding: 2rem;
      max-width: 28rem; width: 100%; border: 1px solid #333;
    }}
    h1 {{ font-size: 1.25rem; margin: 0 0 1rem; color: #00eb91; }}
    p {{ color: #aaa; margin: 0 0 1.25rem; }}
    button, .row {{
      display: block; width: 100%; margin: 0.5rem 0; padding: 0.75rem 1rem;
      border-radius: 8px; border: 1px solid #444; background: #2a2a2a;
      color: #fff; font-size: 1rem; cursor: pointer; text-align: left;
    }}
    button:hover {{ border-color: #00eb91; }}
    input {{
      width: 100%; padding: 0.6rem; margin: 0.4rem 0; border-radius: 6px;
      border: 1px solid #444; background: #111; color: #fff;
      box-sizing: border-box;
    }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Endor Labs</h1>
    <p>Choose how to authenticate (same flow as <code>endorctl init</code>).</p>
    <button type="button" onclick="openAuth('google')">Continue with Google</button>
    <button type="button" onclick="openAuth('github')">Continue with GitHub</button>
    <button type="button" onclick="openAuth('gitlab')">Continue with GitLab</button>
    <button type="button" onclick="openAuth('azureadv2')">
      Continue with Microsoft
    </button>
    <button type="button" onclick="show('emailForm')">Continue with Email</button>
    <button type="button" onclick="show('ssoForm')">Continue with SSO</button>
    <div id="emailForm" class="hidden">
      <input id="emailInput" type="email" placeholder="Email address"
             autocomplete="email"/>
      <button type="button" onclick="openEmail()">Continue</button>
    </div>
    <div id="ssoForm" class="hidden">
      <input id="tenantInput" type="text" placeholder="Tenant name"
             autocomplete="off"/>
      <button type="button" onclick="openSSO()">Continue</button>
    </div>
  </div>
  <script>
    const API = {api_base!r};
    function show(id) {{
      document.getElementById('emailForm').classList.add('hidden');
      document.getElementById('ssoForm').classList.add('hidden');
      document.getElementById(id).classList.remove('hidden');
    }}
    function openAuth(mode) {{
      window.location = API + '/v1/auth/' + mode + '?redirect=cli';
    }}
    function openEmail() {{
      const email = document.getElementById('emailInput').value.trim();
      if (!email) return;
      window.location = API + '/v1/auth/login?email=' + encodeURIComponent(email)
        + '&redirect=cli';
    }}
    function openSSO() {{
      const tenant = document.getElementById('tenantInput').value.trim();
      if (!tenant) return;
      window.location = API + '/v1/auth/sso?tenant=' + encodeURIComponent(tenant)
        + '&redirect=cli';
    }}
  </script>
</body>
</html>
"""


def _auth_selector_page(environment: str) -> bytes:
    api_base = f"https://api.{environment}"
    return _AUTH_SELECTOR_HTML.format(api_base=api_base).encode("utf-8")


@dataclass(frozen=True)
class CallbackSessionSummary:
    """Safe whoami fields for the localhost OAuth success page (never the token)."""

    identity: str | None = None
    auth_source: str | None = None
    expiration_time: str | None = None
    expires_in_label: str | None = None
    tenant_count: int | None = None


def session_summary_from_auth_payload(
    payload: dict[str, object],
    *,
    now: datetime | None = None,
) -> CallbackSessionSummary:
    """Extract display fields from a ``GET /v1/auth`` JSON body."""
    identity = identity_from_auth_payload(payload)

    auth_source = payload.get("authentication_source")
    source = (
        auth_source.strip()
        if isinstance(auth_source, str) and auth_source.strip()
        else None
    )

    expires_at = expiration_from_auth_payload(payload)
    expiration_display: str | None = None
    expires_in_label: str | None = None
    if expires_at is not None:
        expiration_display = format_expiration_utc(expires_at)
        clock = now or datetime.now(UTC)
        expires_in_label = format_ttl_label((expires_at - clock).total_seconds())

    tenants = payload.get("tenants")
    if isinstance(tenants, list):
        tenant_count: int | None = len(cast("list[object]", tenants))
    else:
        tenant_count = None

    return CallbackSessionSummary(
        identity=identity,
        auth_source=source,
        expiration_time=expiration_display,
        expires_in_label=expires_in_label,
        tenant_count=tenant_count,
    )


def fetch_auth_session(
    token: str,
    *,
    environment: str = DEFAULT_ENV,
) -> dict[str, object] | None:
    """Validate a captured bearer via ``GET /v1/auth`` (no token logging)."""
    import httpx

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"https://api.{environment}/v1/auth",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return cast("dict[str, object]", payload)


def _summary_after_token_capture(
    token: str,
    *,
    environment: str,
) -> CallbackSessionSummary | None:
    """Fetch whoami for the success page and emit audit logs (never the token)."""
    payload = fetch_auth_session(token, environment=environment)
    if payload is None:
        logger.error(
            "Callback whoami failed after token capture; session summary unavailable"
        )
        return None
    summary = session_summary_from_auth_payload(payload)
    if summary.identity:
        logger.info(
            "Callback whoami identity=%s ttl=%s",
            summary.identity,
            summary.expires_in_label or "unknown",
        )
    else:
        logger.info(
            "Callback whoami ok (no identity field) ttl=%s",
            summary.expires_in_label or "unknown",
        )
    return summary


_SUCCESS_PAGE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Authentication Successful</title>
  <style>
    body {{
      font-family: system-ui, sans-serif; background: #0a0a0a; color: #fff;
      min-height: 100vh; display: flex; align-items: center;
      justify-content: center; margin: 0;
    }}
    .box {{
      background: #1a1a1a; border-radius: 12px; padding: 2rem;
      max-width: 28rem; width: 100%; border: 1px solid #333;
    }}
    h1 {{ font-size: 1.25rem; margin: 0 0 0.5rem; color: #00eb91; }}
    .sub {{ color: #aaa; margin: 0 0 1.25rem; }}
    dl {{
      margin: 0 0 1.5rem; display: grid;
      grid-template-columns: auto 1fr; gap: 0.4rem 1rem;
    }}
    dt {{ color: #888; }}
    dd {{ margin: 0; word-break: break-word; }}
    a.btn {{
      display: inline-block; padding: 0.75rem 1rem; border-radius: 8px;
      border: 1px solid #00eb91; color: #00eb91; text-decoration: none;
    }}
    a.btn:hover {{ background: #0f2a20; }}
    .note {{ color: #666; font-size: 0.85rem; margin: 1rem 0 0; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Authentication successful</h1>
    <p class="sub">You can close this tab and return to the terminal.</p>
    {details}
    <a class="btn" href="{app_url}">Open Endor Labs</a>
    <p class="note">The bearer token was captured locally and is not shown here.</p>
  </div>
</body>
</html>
"""


def _success_page(
    environment: str,
    summary: CallbackSessionSummary | None = None,
) -> bytes:
    """Render the localhost callback success page (identity + TTL, never the token)."""
    app_url = f"https://app.{environment}"
    rows: list[str] = []
    if summary is not None:
        if summary.identity:
            rows.append(f"<dt>Identity</dt><dd>{escape(summary.identity)}</dd>")
        if summary.auth_source:
            rows.append(f"<dt>Auth source</dt><dd>{escape(summary.auth_source)}</dd>")
        if summary.expires_in_label:
            rows.append(
                f"<dt>Token TTL</dt><dd>{escape(summary.expires_in_label)} remaining"
                "</dd>"
            )
        if summary.expiration_time:
            rows.append(f"<dt>Expires</dt><dd>{escape(summary.expiration_time)}</dd>")
        if summary.tenant_count is not None:
            rows.append(f"<dt>Tenants</dt><dd>{summary.tenant_count}</dd>")
    details = f"<dl>{''.join(rows)}</dl>" if rows else ""
    return _SUCCESS_PAGE_HTML.format(
        details=details,
        app_url=escape(app_url, quote=True),
    ).encode("utf-8")


def _make_token_handler(
    expected_state: str,
    *,
    environment: str = DEFAULT_ENV,
    serve_selector: bool = False,
) -> type[BaseHTTPRequestHandler]:
    """Build a callback handler that validates OAuth CSRF state before capture."""

    class TokenHandler(BaseHTTPRequestHandler):
        """HTTP request handler for OAuth callback that captures the bearer token."""

        def do_GET(self) -> None:
            """Handle GET: optional auth-selector, then OAuth redirect with token."""
            global _captured_token
            try:
                parsed_url = urlparse(self.path)
                path = parsed_url.path or "/"

                if path == "/favicon.ico":
                    self.send_response(404)
                    self.end_headers()
                    return

                if (
                    serve_selector
                    and path in {"/", "/auth-selector"}
                    and not parsed_url.query
                ):
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    with contextlib.suppress(Exception):
                        _ = self.wfile.write(_auth_selector_page(environment))
                    return

                if not parsed_url.query:
                    logger.warning("No query parameters in redirect: %s", self.path)
                    self.send_response(404)
                    self.end_headers()
                    return

                params = parse_qs(parsed_url.query, keep_blank_values=False)
                # Endor CLI redirects (`redirect=cli`) currently return only
                # `token` and do not echo `state`. Enforce CSRF only when the
                # platform includes a state parameter on the callback.
                states = params.get("state", [])
                if states and (len(states) != 1 or states[0] != expected_state):
                    logger.warning("OAuth state mismatch in redirect")
                    self.send_response(400)
                    self.end_headers()
                    return

                tokens = params.get("token", [])
                if len(tokens) == 1 and tokens[0]:
                    _captured_token = tokens[0]
                    logger.info("Token captured successfully")
                    summary = _summary_after_token_capture(
                        _captured_token,
                        environment=environment,
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    with contextlib.suppress(Exception):
                        _ = self.wfile.write(
                            _success_page(environment, summary=summary)
                        )
                else:
                    logger.warning("Token not found in redirect: %s", self.path)
                    self.send_response(302)
                    self.send_header(
                        "Location", f"https://app.{environment}/endorctl-success"
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
            self.do_GET()

        @override
        def log_message(self, format: str, *args: Any, **_kwargs: Any) -> None:
            """Suppress default HTTP server logs."""
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("HTTP Server: %s", format % args)

    return TokenHandler


# Backward-compatible default handler class for tests that import TokenHandler directly.
TokenHandler = _make_token_handler("")


def _append_query_params(url: str, params: dict[str, str]) -> str:
    """Merge *params* into *url* using proper URL encoding."""
    split = urlsplit(url)
    existing = parse_qs(split.query, keep_blank_values=False)
    merged: dict[str, str] = {
        key: values[0] for key, values in existing.items() if values
    }
    merged.update(params)
    query = urlencode(merged)
    return urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))


def _bind_callback_server(
    expected_state: str,
    *,
    environment: str = DEFAULT_ENV,
    serve_selector: bool = False,
) -> tuple[HTTPServer, int]:
    """Bind localhost callback server on the first free port in the CLI range."""
    last_error: OSError | None = None
    handler = _make_token_handler(
        expected_state,
        environment=environment,
        serve_selector=serve_selector,
    )
    for offset in range(OAUTH_CALLBACK_PORT_COUNT):
        port = OAUTH_CALLBACK_PORT_START + offset
        try:
            server = HTTPServer(("localhost", port), handler)
            return server, port
        except OSError as exc:
            last_error = exc
            if "Address already in use" not in str(exc):
                raise
    if last_error is not None:
        raise last_error
    raise OSError("Unable to bind OAuth callback server")


def get_token(  # noqa: C901
    timeout: int = 20,
    environment: str = DEFAULT_ENV,
    browser_name: str | None = None,
    method: str = "browser-auth",
    email: str | None = None,
    auth_tenant: str | None = None,
) -> str | None:
    """Get bearer token via browser OAuth flow.

    Starts a local HTTP server on localhost in the 30000-30009 range, opens a
    browser to the OAuth URL (or local auth selector), and captures the token
    from the redirect callback.

    ⚠️  WARNING: This function requires human interaction (opens browser window)
    and cannot be used in CI/CD environments. Use API key authentication instead.

    Args:
        timeout: Server timeout in seconds (default: 20)
        environment: API environment domain (default: "endorlabs.com")
        browser_name: Browser name for webbrowser.get() (optional)
        method: Auth method. Documented: ``sso`` (requires ``auth_tenant``),
            ``google``, ``github``, ``gitlab``, ``email`` (requires ``email``).
            Experimental: ``browser-auth`` (local provider picker), ``azureadv2``.
            Aliases ``browser`` / ``admin`` → ``browser-auth``.
        email: Address for email magic-link authentication (required if method='email')
        auth_tenant: Tenant name required if method='sso'.

    Returns:
        Bearer token string or None if authentication failed or timed out

    Raises:
        ValidationError: If method is not supported, email/tenant required but
            not provided, or if called in a CI/CD environment

    """
    global _captured_token
    _captured_token = None

    # Detect CI/CD environments and prevent browser auth
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "BUILDKITE",
        "CIRCLECI",
    ]
    is_ci = any(os.getenv(indicator) for indicator in ci_indicators)

    if is_ci:
        raise ValidationError(
            "Browser authentication cannot be used in CI/CD environments. "
            "Browser authentication requires human interaction (opens browser window). "
            "Use API key authentication instead by setting ENDOR_API_CREDENTIALS_KEY "
            "and ENDOR_API_CREDENTIALS_SECRET environment variables."
        )

    raw_method = method.strip().lower()
    normalized_method = _METHOD_ALIASES.get(raw_method, raw_method)

    if normalized_method == "browser-auth":
        expected_state = secrets.token_urlsafe(32)
        try:
            server, port = _bind_callback_server(
                expected_state,
                environment=environment,
                serve_selector=True,
            )
            server.timeout = timeout
            browser = get_browser(browser_name)
            selector_url = f"http://localhost:{port}/auth-selector"
            logger.info("Opening browser for auth-selector...")
            _ = browser.open_new_tab(selector_url)
            logger.info(
                "Waiting for OAuth callback on localhost:%s (timeout: %ss)...",
                port,
                timeout,
            )
            deadline = time.monotonic() + timeout
            poll_timeout = min(2.0, float(timeout))
            while time.monotonic() < deadline and not _captured_token:
                remaining = deadline - time.monotonic()
                server.timeout = min(poll_timeout, max(remaining, 0.1))
                _ = server.handle_request()
            server.server_close()
            if _captured_token:
                logger.info("Browser authentication successful")
                return _captured_token
            logger.warning("No token received from OAuth callback")
            return None
        except OSError as e:
            if "Address already in use" in str(e):
                logger.error(
                    "OAuth callback ports %s-%s are in use. "
                    "Close other applications using these ports.",
                    OAUTH_CALLBACK_PORT_START,
                    OAUTH_CALLBACK_PORT_START + OAUTH_CALLBACK_PORT_COUNT - 1,
                )
            else:
                logger.error("Unable to start OAuth server: %s", e)
            return None
        except Exception as e:
            logger.error("Unable to complete browser authentication: %s", e)
            return None

    if normalized_method not in AUTH_METHODS:
        supported = ", ".join(["browser-auth", *sorted(AUTH_METHODS)])
        raise ValidationError(
            f"Unsupported auth method: {normalized_method}. "
            f"Supported methods: {supported}"
        )

    if normalized_method == "email" and not email:
        raise ValidationError("Email address required for email-based authentication")

    if normalized_method == "sso" and not auth_tenant:
        raise ValidationError(
            "Tenant is required for sso authentication "
            "(pass auth_tenant= or ENDOR_NAMESPACE / -n)."
        )

    expected_state = secrets.token_urlsafe(32)

    auth_url_template = AUTH_METHODS[normalized_method]
    if "{tenant}" in auth_url_template:
        auth_url = auth_url_template.format(
            environment=environment,
            tenant=auth_tenant,
        )
    else:
        auth_url = auth_url_template.format(environment=environment)

    extra_params: dict[str, str] = {
        "redirect": "cli",
        "state": expected_state,
    }
    if normalized_method == "email" and email:
        extra_params["email"] = email
    auth_url = _append_query_params(auth_url, extra_params)

    try:
        server, port = _bind_callback_server(
            expected_state,
            environment=environment,
            serve_selector=False,
        )
        server.timeout = timeout

        browser = get_browser(browser_name)
        logger.info("Opening browser for %s authentication...", normalized_method)
        _ = browser.open_new_tab(auth_url)

        logger.info(
            "Waiting for OAuth callback on localhost:%s (timeout: %ss)...",
            port,
            timeout,
        )

        # Keep accepting requests until timeout or a token is captured so a
        # stale localhost tab / favicon cannot consume the single handle_request.
        deadline = time.monotonic() + timeout
        poll_timeout = min(2.0, float(timeout))
        while time.monotonic() < deadline and not _captured_token:
            remaining = deadline - time.monotonic()
            server.timeout = min(poll_timeout, max(remaining, 0.1))
            _ = server.handle_request()
        server.server_close()

        if _captured_token:
            logger.info("Browser authentication successful")
            return _captured_token
        logger.warning("No token received from OAuth callback")
        return None

    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(
                "OAuth callback ports %s-%s are in use. "
                "Close other applications using these ports.",
                OAUTH_CALLBACK_PORT_START,
                OAUTH_CALLBACK_PORT_START + OAUTH_CALLBACK_PORT_COUNT - 1,
            )
        else:
            logger.error("Unable to start OAuth server: %s", e)
        return None
    except Exception as e:
        logger.error("Unable to complete browser authentication: %s", e)
        return None
