"""Tenant EndorLicense feature entitlements for report packet gating."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.reports.analyze.finding_burndown_specs import (
    CATEGORY_AI_SAST,
    CATEGORY_SAST,
    CATEGORY_SECRETS,
    CODE_CATEGORIES,
)

if TYPE_CHECKING:
    from endorlabs import Client

FEATURE_SCA = "ENDOR_LICENSE_FEATURE_TYPE_SCA"
FEATURE_SAST = "ENDOR_LICENSE_FEATURE_TYPE_SAST"
FEATURE_AI_SAST = "ENDOR_LICENSE_FEATURE_TYPE_AI_SAST"
FEATURE_SECRETS = "ENDOR_LICENSE_FEATURE_TYPE_SECRETS"
FEATURE_ENDOR_PATCHING = "ENDOR_LICENSE_FEATURE_TYPE_ENDOR_PATCHING"

CODE_CATEGORY_FEATURES: dict[str, str] = {
    CATEGORY_SAST: FEATURE_SAST,
    CATEGORY_AI_SAST: FEATURE_AI_SAST,
    CATEGORY_SECRETS: FEATURE_SECRETS,
}

SKIP_REASON_NOT_ENTITLED = "not_entitled"
SKIP_REASON_OPT_IN = "opt_in"


def _info_type(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("type") or "")
    return str(getattr(row, "type", None) or "")


def _info_expiration(row: Any) -> datetime | None:
    raw = (
        row.get("expiration_time")
        if isinstance(row, dict)
        else getattr(row, "expiration_time", None)
    )
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    text = str(raw).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _feature_active(row: Any, *, now: datetime) -> bool:
    feat = _info_type(row)
    if not feat or feat.endswith("_UNSPECIFIED"):
        return False
    exp = _info_expiration(row)
    return not (exp is not None and exp <= now)


def feature_types_from_license(
    license_row: Any, *, now: datetime | None = None
) -> set[str]:
    """Return active feature type strings from one EndorLicense row."""
    when = now or datetime.now(UTC)
    spec = (
        license_row.get("spec")
        if isinstance(license_row, dict)
        else getattr(license_row, "spec", None)
    )
    if spec is None:
        return set()
    infos = (
        spec.get("license_info")
        if isinstance(spec, dict)
        else getattr(spec, "license_info", None)
    ) or []
    excluded_raw = (
        spec.get("excluded_feature_types")
        if isinstance(spec, dict)
        else getattr(spec, "excluded_feature_types", None)
    ) or []
    excluded = {str(x) for x in excluded_raw if x}
    active = {
        _info_type(row)
        for row in infos
        if _feature_active(row, now=when) and _info_type(row) not in excluded
    }
    return active - excluded


def fetch_license_feature_types(
    client: Client,
    namespace: str,
) -> set[str] | None:
    """List EndorLicense for *namespace* and return active feature types.

    Returns ``None`` when the license list fails or is empty so callers can
    fail open (keep requested slices) rather than silently drop entitled data.
    """
    try:
        rows = list(
            client.EndorLicense.list(
                namespace=namespace,
                traverse=False,
                max_pages=1,
            )
        )
    # Broad catch: entitlement probe must not abort packet construction.
    except Exception:
        return None
    if not rows:
        return None
    features: set[str] = set()
    now = datetime.now(UTC)
    for row in rows:
        features |= feature_types_from_license(row, now=now)
    return features


def entitled_code_categories(features: set[str]) -> list[str]:
    """Return code-burndown category keys covered by *features* (stable order)."""
    return [key for key in CODE_CATEGORIES if CODE_CATEGORY_FEATURES[key] in features]


def has_endor_patching(features: set[str]) -> bool:
    """True when Endor Patching is an active license feature."""
    return FEATURE_ENDOR_PATCHING in features
