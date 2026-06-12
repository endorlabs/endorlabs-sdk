"""Opt-in wire-key probes for maintainer debugging (not on the default parse path).

Primary API shape drift detection is model-sync + CI parity — see
docs/contributing/docs-drift-workflow.md.
"""

from __future__ import annotations

from typing import Any

from .logging_config import get_resource_logger

logger = get_resource_logger(__name__)

# Keys commonly present on list responses but not modeled on consumer types.
_KNOWN_IGNORED_WIRE_KEYS = frozenset(
    {
        "tenant",
        "data",
        "will_be_deleted_at",
        "search_score",
        "scan_time",
    }
)


def unknown_wire_keys(
    data: dict[str, Any],
    model_fields: set[str],
    *,
    ignored_keys: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Return wire keys in ``data`` that are not in ``model_fields``."""
    ignore = _KNOWN_IGNORED_WIRE_KEYS if ignored_keys is None else ignored_keys
    return {
        key: value
        for key, value in data.items()
        if key not in model_fields and key not in ignore
    }


def log_unknown_wire_keys(
    data: dict[str, Any],
    model_fields: set[str],
    *,
    context: str = "",
    resource_name: str | None = None,
    ignored_keys: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Log unknown wire keys and return them (explicit opt-in probe)."""
    unknown = unknown_wire_keys(data, model_fields, ignored_keys=ignored_keys)
    if not unknown:
        return unknown
    field_list = ", ".join(sorted(unknown))
    prefix = f"{resource_name}." if resource_name else ""
    message = f"Wire key probe {prefix}{context}: unknown keys {field_list}"
    logger.warning(message)
    for key, value in unknown.items():
        logger.debug(
            "Unknown wire key %r: %s = %r",
            key,
            type(value).__name__,
            value,
        )
    return unknown
