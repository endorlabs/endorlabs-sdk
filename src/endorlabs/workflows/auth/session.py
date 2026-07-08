"""Auth environment probe, session verification, and browser token refresh.

Composable entrypoints:

- ``scan_auth_env`` — env-key presence (booleans only, no secrets).
- ``probe_endorctl`` — local ``endorctl`` on PATH and config path.
- ``verify_auth`` — bundles the above plus ``Client().whoami()`` when creds exist.
- ``refresh_token_to_dotenv`` — interactive browser OAuth into a dotenv file.

Use ``verify_auth`` for step-zero checks; call ``scan_auth_env`` or ``probe_endorctl``
alone when you only need one probe.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from endorlabs.core.exceptions import ValidationError
from endorlabs.utils.endorctl_config import (
    endorctl_config_path,
    read_endorctl_namespace,
)
from endorlabs.utils.redaction import (
    JSON_REDACTION_REPLACEMENT,
    REDACTION_DEFAULT_REPLACEMENT,
    json_redaction_pattern,
    redaction_pattern,
    url_token_redaction_pattern,
    url_token_redaction_replacement,
)

from .dotenv import read_env_or_dotenv, upsert_dotenv_key
from .env_resolution import (
    browser_method_from_auth_payload,
    resolve_auth_mode_resolved,
    resolve_sso_tenant,
)

if TYPE_CHECKING:
    from endorlabs.core.whoami import WhoamiResult

BrowserAuthMethod = Literal["sso", "google", "github", "gitlab", "email"]
AuthStatus = Literal[
    "ready",
    "missing_credentials",
    "dual_mode_conflict",
    "verification_failed",
]

_NAMESPACE_ENV_KEY = "ENDOR_NAMESPACE"
_SUPPORTED_BROWSER_METHODS = frozenset({"sso", "google", "github", "gitlab", "email"})

_REDACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (redaction_pattern, REDACTION_DEFAULT_REPLACEMENT),
    (json_redaction_pattern, JSON_REDACTION_REPLACEMENT),
    (url_token_redaction_pattern, url_token_redaction_replacement),
)


def redact_sensitive_text(message: str | None) -> str | None:
    """Scrub credential-shaped substrings before CLI/JSON output."""
    if not message:
        return message
    text = message
    for pattern, replacement in _REDACTION_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


@dataclass(frozen=True)
class AuthEnvironmentScan:
    """Presence of credential env keys (never includes secret values)."""

    has_bearer_token: bool
    has_api_key: bool
    has_api_secret: bool
    has_namespace_env: bool
    dual_mode_conflict: bool
    endor_namespace_set: bool
    endorctl_config_present: bool
    endorctl_namespace_configured: bool

    @property
    def has_api_key_pair(self) -> bool:
        """True when both API key env vars are set."""
        return self.has_api_key and self.has_api_secret

    @property
    def has_any_credentials(self) -> bool:
        """True when bearer token or a full API key pair is configured."""
        return self.has_bearer_token or self.has_api_key_pair


@dataclass(frozen=True)
class EndorctlProbe:
    """Local endorctl installation probe (no user-controlled argv)."""

    on_path: bool
    executable: str | None
    version: str | None
    config_path: str
    config_exists: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize probe fields for JSON output."""
        return asdict(self)


@dataclass(frozen=True)
class AuthVerification:
    """Result of ``verify_auth``."""

    status: AuthStatus
    environment: AuthEnvironmentScan
    endorctl: EndorctlProbe
    whoami: WhoamiResult | None = None
    namespace_source: str | None = None
    auth_mode_resolved: str | None = None
    sso_tenant_resolved: str | None = None
    browser_auth_method_resolved: str | None = None
    error: str | None = None
    next_steps: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Serialize verification result for JSON output."""
        payload: dict[str, Any] = {
            "status": self.status,
            "environment": asdict(self.environment),
            "endorctl": self.endorctl.to_dict(),
            "next_steps": list(self.next_steps),
        }
        if self.auth_mode_resolved:
            payload["auth_mode_resolved"] = self.auth_mode_resolved
        if self.sso_tenant_resolved:
            payload["sso_tenant_resolved"] = self.sso_tenant_resolved
        if self.browser_auth_method_resolved:
            payload["browser_auth_method_resolved"] = self.browser_auth_method_resolved
        if self.whoami is not None:
            payload["whoami"] = {
                "identity": self.whoami.identity,
                "auth_type": self.whoami.auth_type,
                "expiration_time": (
                    self.whoami.expiration_time.isoformat()
                    if self.whoami.expiration_time
                    else None
                ),
                "expires_in_seconds": self.whoami.expires_in_seconds,
                "is_expired": self.whoami.is_expired,
            }
        if self.namespace_source:
            payload["namespace_source"] = self.namespace_source
        if self.error:
            payload["error"] = redact_sensitive_text(self.error)
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        """Return ``to_dict()`` as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def scan_auth_env() -> AuthEnvironmentScan:
    """Report which auth-related env keys are set (booleans only, never values)."""
    token = os.getenv("ENDOR_TOKEN", "").strip()
    key = os.getenv("ENDOR_API_CREDENTIALS_KEY", "").strip()
    secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET", "").strip()
    namespace = os.getenv(_NAMESPACE_ENV_KEY, "").strip()
    config_path = endorctl_config_path()
    config_ns = read_endorctl_namespace()
    return AuthEnvironmentScan(
        has_bearer_token=bool(token),
        has_api_key=bool(key),
        has_api_secret=bool(secret),
        has_namespace_env=bool(namespace),
        dual_mode_conflict=bool(token and key and secret),
        endor_namespace_set=bool(namespace),
        endorctl_config_present=config_path.is_file(),
        endorctl_namespace_configured=bool(config_ns),
    )


def probe_endorctl() -> EndorctlProbe:
    """Detect endorctl on PATH and read ``--version`` with a fixed argv."""
    executable = shutil.which("endorctl") or shutil.which("endorctl.exe")
    version: str | None = None
    if executable:
        try:
            result = subprocess.run(  # noqa: S603
                [executable, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            version = None
        else:
            if result.returncode == 0:
                version = (result.stdout or result.stderr or "").strip() or None
    config_path = endorctl_config_path()
    return EndorctlProbe(
        on_path=executable is not None,
        executable=executable,
        version=version,
        config_path=str(config_path),
        config_exists=config_path.is_file(),
    )


def resolve_api_environment(env_file: Path | None = None) -> str:
    """Return API host segment for browser auth URLs."""
    path = env_file or Path(".env")
    api_base = read_env_or_dotenv("ENDOR_API", path) or "https://api.endorlabs.com"
    environment = api_base.replace("https://api.", "").replace("http://api.", "")
    if environment == api_base:
        environment = "endorlabs.com"
    return environment


def build_browser_auth_kwargs(
    *,
    method: BrowserAuthMethod,
    namespace: str | None,
    env_file: Path,
    environment: str,
    timeout: int,
    email: str | None = None,
) -> dict[str, object]:
    """Build kwargs for ``endorlabs.auth_server.get_token``."""
    normalized = method.strip().lower()
    if normalized not in _SUPPORTED_BROWSER_METHODS:
        supported = ", ".join(sorted(_SUPPORTED_BROWSER_METHODS))
        raise ValueError(
            f"Unsupported browser auth method '{method}'. Use: {supported}"
        )

    if normalized == "email" and not (email and email.strip()):
        raise ValueError("email is required when method is 'email'")

    if normalized == "sso":
        tenant = resolve_sso_tenant(namespace=namespace, env_file=env_file)
        if not tenant:
            raise ValueError(
                "Tenant SSO requires --namespace / -n or ENDOR_NAMESPACE "
                f"(environment or {env_file}), or ENDOR_NAMESPACE in "
                f"{endorctl_config_path()}"
            )
        return {
            "timeout": timeout,
            "environment": environment,
            "method": "sso",
            "auth_tenant": tenant,
        }

    kwargs: dict[str, object] = {
        "timeout": timeout,
        "environment": environment,
        "method": normalized,
    }
    if normalized == "email":
        kwargs["email"] = email
    return kwargs


def refresh_token_to_dotenv(
    env_file: Path,
    *,
    method: BrowserAuthMethod = "sso",
    namespace: str | None = None,
    environment: str | None = None,
    timeout: int = 120,
    email: str | None = None,
) -> Path:
    """Run interactive browser OAuth and upsert ``ENDOR_TOKEN`` in *env_file*.

    Does not print the token. Requires a human for the browser callback unless
    CI uses API keys instead (see skill ``endor-auth-setup``).
    """
    from endorlabs.auth_server import get_token

    env_file = env_file.resolve()
    api_environment = environment or resolve_api_environment(env_file)
    token_kwargs = build_browser_auth_kwargs(
        method=method,
        namespace=namespace,
        env_file=env_file,
        environment=api_environment,
        timeout=timeout,
        email=email,
    )
    token = get_token(**token_kwargs)
    if not token:
        raise RuntimeError("Browser authentication failed or timed out.")
    upsert_dotenv_key(env_file, "ENDOR_TOKEN", token)
    return env_file


def _namespace_resolution_label(tenant: str | None) -> str | None:
    if tenant:
        return "tenant_argument"
    if os.getenv(_NAMESPACE_ENV_KEY, "").strip():
        return "env"
    if read_endorctl_namespace():
        return "endorctl_config"
    return None


def _build_next_steps(
    scan: AuthEnvironmentScan,
    endorctl: EndorctlProbe,
    *,
    error: str | None,
) -> tuple[str, ...]:
    steps: list[str] = []
    if scan.dual_mode_conflict:
        steps.append(
            "Unset either ENDOR_TOKEN or both ENDOR_API_CREDENTIALS_KEY and "
            "ENDOR_API_CREDENTIALS_SECRET (single auth mode for SDK, endorctl, MCP)."
        )
        return tuple(steps)

    if scan.has_bearer_token and not scan.has_namespace_env:
        steps.append(
            "Set ENDOR_NAMESPACE (or pass -n / --tenant) for SSO tenant resolution "
            "and Client namespace defaults."
        )

    if not scan.has_any_credentials:
        if endorctl.on_path:
            steps.append(
                "Run endorctl init --auth-mode=sso --auth-tenant=<tenant> "
                f"(config: {endorctl.config_path})."
            )
            steps.append(
                "Or set ENDOR_API_CREDENTIALS_KEY + ENDOR_API_CREDENTIALS_SECRET "
                "and ENDOR_NAMESPACE in .env."
            )
        else:
            steps.append(
                "Set ENDOR_API_CREDENTIALS_KEY + ENDOR_API_CREDENTIALS_SECRET "
                "and ENDOR_NAMESPACE in .env for API-key auth."
            )
        steps.append(
            "For interactive browser SSO into .env: "
            "uv run endor-auth refresh --method sso -n <tenant>"
        )
        return tuple(steps)

    if error:
        if "401" in error or "Unauthorized" in error:
            steps.append(
                "Bearer token may be expired — run: "
                "uv run endor-auth refresh --method sso -n <tenant>"
            )
        elif "403" in error or "Forbidden" in error:
            steps.append(
                "Credential may lack access to the target tenant — "
                "verify ENDOR_NAMESPACE and token scope."
            )
        else:
            steps.append(
                "Verify credentials with: uv run endor-auth check --tenant <tenant>"
            )
        steps.append(
            "Or refresh browser token: "
            "uv run endor-auth refresh --method sso -n <tenant>"
        )
    return tuple(steps)


def verify_auth(
    tenant: str | None = None,
) -> AuthVerification:
    """Probe env, endorctl, and ``Client().whoami()`` when credentials exist.

    Orchestrates :func:`scan_auth_env`, :func:`probe_endorctl`, and a live
    whoami call. Returns structured ``status`` and ``next_steps`` — use
    :meth:`AuthVerification.to_json` for agent output. Never includes secret
    values in errors (see :func:`redact_sensitive_text`).
    """
    scan = scan_auth_env()
    endorctl = probe_endorctl()
    ns_source = _namespace_resolution_label(tenant)
    auth_mode = resolve_auth_mode_resolved(
        has_bearer_token=scan.has_bearer_token,
        has_api_key_pair=scan.has_api_key_pair,
        dual_mode_conflict=scan.dual_mode_conflict,
    )
    sso_tenant = resolve_sso_tenant(namespace=tenant)

    def _verification(
        **kwargs: object,
    ) -> AuthVerification:
        whoami = kwargs.get("whoami")
        resolved_browser: str | None = None
        if whoami is not None:
            resolved_browser = browser_method_from_auth_payload(
                {
                    "authentication_source": whoami.authentication_source,
                    "user": {"spec": {"email": whoami.identity}},
                }
            )
        return AuthVerification(
            auth_mode_resolved=auth_mode,
            sso_tenant_resolved=sso_tenant,
            browser_auth_method_resolved=resolved_browser,
            **kwargs,
        )

    if scan.dual_mode_conflict:
        return _verification(
            status="dual_mode_conflict",
            environment=scan,
            endorctl=endorctl,
            namespace_source=ns_source,
            next_steps=_build_next_steps(scan, endorctl, error=None),
        )

    if not scan.has_any_credentials:
        return _verification(
            status="missing_credentials",
            environment=scan,
            endorctl=endorctl,
            namespace_source=ns_source,
            next_steps=_build_next_steps(scan, endorctl, error=None),
        )

    import endorlabs

    try:
        client = endorlabs.Client(tenant=tenant)
        whoami = client.whoami()
        client.close()
    except ValidationError as exc:
        message = redact_sensitive_text(str(exc)) or str(exc)
        return _verification(
            status="verification_failed",
            environment=scan,
            endorctl=endorctl,
            namespace_source=ns_source,
            error=message,
            next_steps=_build_next_steps(scan, endorctl, error=message),
        )
    except Exception as exc:
        message = redact_sensitive_text(str(exc)) or str(exc)
        return _verification(
            status="verification_failed",
            environment=scan,
            endorctl=endorctl,
            namespace_source=ns_source,
            error=message,
            next_steps=_build_next_steps(scan, endorctl, error=message),
        )

    if not whoami.identity:
        return _verification(
            status="verification_failed",
            environment=scan,
            endorctl=endorctl,
            whoami=whoami,
            namespace_source=ns_source,
            error="whoami returned no identity",
            next_steps=_build_next_steps(scan, endorctl, error="no identity"),
        )

    return _verification(
        status="ready",
        environment=scan,
        endorctl=endorctl,
        whoami=whoami,
        namespace_source=ns_source,
        next_steps=tuple(),
    )
