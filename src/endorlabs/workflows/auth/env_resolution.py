"""Auth environment resolution aligned with endorctl Tier A variables.

SSO tenant for refresh and Client reauth uses the root segment of a namespace
(``acme.child`` → ``acme``). Precedence matches endorctl SSO init:

``-n`` / explicit namespace  >  ``ENDOR_NAMESPACE`` (process env)  >
``ENDOR_NAMESPACE`` (``.env``)  >  ``ENDOR_NAMESPACE`` in endorctl ``config.yaml``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from endorlabs.utils.endorctl_config import read_endorctl_namespace
from endorlabs.workflows.wire_access import as_dict, nested_str

from .dotenv import read_env_or_dotenv

_NAMESPACE_ENV_KEY = "ENDOR_NAMESPACE"
_SUPPORTED_BROWSER_REFRESH_METHODS = frozenset(
    {"browser-auth", "sso", "google", "github", "gitlab", "email", "azureadv2"}
)
_BROWSER_METHOD_ALIASES: dict[str, str] = {
    "browser": "browser-auth",
    "admin": "browser-auth",
}
# Custom SSO IdPs report authentication_source as a 24-char hex object id.
_IDP_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")


def _looks_like_idp_object_id(value: str) -> bool:
    return bool(_IDP_OBJECT_ID_RE.fullmatch(value.strip().lower()))


def normalize_browser_auth_method(method: str | None) -> str | None:
    """Normalize refresh/reauth method names to supported browser providers."""
    if not method or not method.strip():
        return None
    cleaned = method.strip().lower()
    cleaned = _BROWSER_METHOD_ALIASES.get(cleaned, cleaned)
    if cleaned in _SUPPORTED_BROWSER_REFRESH_METHODS:
        return cleaned
    return None


def browser_method_from_authentication_source(source: str | None) -> str | None:
    """Map ``GET /v1/auth`` ``authentication_source`` to a browser refresh method."""
    if not source or not source.strip():
        return None
    cleaned = source.strip().lower()
    direct = normalize_browser_auth_method(cleaned)
    if direct:
        return direct
    if "google" in cleaned:
        return "google"
    if "github" in cleaned:
        return "github"
    if "gitlab" in cleaned:
        return "gitlab"
    # Email magic-link sessions report ``authentication_source=endor``.
    if cleaned == "endor" or "email" in cleaned:
        return "email"
    if any(marker in cleaned for marker in ("sso", "saml", "oidc")):
        return "sso"
    # Tenant SSO often uses the IdP config object id as authentication_source.
    if _looks_like_idp_object_id(cleaned):
        return "sso"
    return None


def browser_method_from_user_identity(identity: str | None) -> str | None:
    """Infer provider from canonical identity strings (e.g. ``user@corp@google``)."""
    if not identity or not identity.strip():
        return None
    cleaned = identity.strip().lower()
    for provider in ("google", "github", "gitlab"):
        if f"@{provider}" in cleaned:
            return provider
    # Email magic-link identities use ``addr@endor`` (e.g. ``a@b.com@endor``).
    if cleaned.endswith("@endor") or "@endor@" in cleaned:
        return "email"
    # Custom SSO identities append ``@<idp-object-id>``.
    if "@" in cleaned:
        suffix = cleaned.rsplit("@", 1)[-1]
        if _looks_like_idp_object_id(suffix):
            return "sso"
    return None


def browser_method_from_auth_payload(payload: dict[str, object]) -> str | None:
    """Infer browser refresh method from ``/v1/auth`` user metadata."""
    source = payload.get("authentication_source")
    auth_source = str(source) if isinstance(source, str) and source.strip() else None
    resolved = browser_method_from_authentication_source(auth_source)
    if resolved:
        return resolved

    user = as_dict(payload.get("user"))
    name = nested_str(user, "meta", "name")
    if name:
        resolved = browser_method_from_user_identity(name)
        if resolved:
            return resolved
    email = nested_str(user, "spec", "email")
    if email:
        resolved = browser_method_from_user_identity(email)
        if resolved:
            return resolved
    return None


def resolve_bearer_browser_method(
    *,
    explicit: str | None = None,
    authentication_source: str | None = None,
) -> str | None:
    """Resolve bearer reauth method from explicit override or ``/v1/auth`` source."""
    if explicit:
        return normalize_browser_auth_method(explicit)
    return browser_method_from_authentication_source(authentication_source)


def sso_tenant_from_namespace(namespace: str) -> str:
    """Use the root tenant segment for SSO (``tenant.child`` → ``tenant``)."""
    cleaned = namespace.strip()
    if not cleaned:
        return ""
    return cleaned.split(".", 1)[0]


def resolve_sso_tenant(
    *,
    namespace: str | None,
    env_file: Path | None = None,
) -> str | None:
    """Resolve SSO tenant from explicit namespace, env, dotenv, or endorctl config."""
    if namespace and namespace.strip():
        return sso_tenant_from_namespace(namespace)

    path = env_file or Path(".env")

    env_ns = os.getenv(_NAMESPACE_ENV_KEY, "").strip()
    if env_ns:
        tenant = sso_tenant_from_namespace(env_ns)
        if tenant:
            return tenant

    dotenv_ns = read_env_or_dotenv(_NAMESPACE_ENV_KEY, path)
    if dotenv_ns:
        tenant = sso_tenant_from_namespace(dotenv_ns)
        if tenant:
            return tenant

    config_ns = read_endorctl_namespace()
    if config_ns:
        tenant = sso_tenant_from_namespace(config_ns)
        if tenant:
            return tenant

    return None


def resolve_auth_mode_resolved(
    *,
    has_bearer_token: bool,
    has_api_key_pair: bool,
    dual_mode_conflict: bool,
) -> str | None:
    """Return resolved credential mode label for ``endor-auth check`` JSON."""
    if dual_mode_conflict:
        return None
    if has_bearer_token:
        return "bearer"
    if has_api_key_pair:
        return "api-key"
    return None
