"""Load and validate customer user-space profile for SDK reference docs and op trims."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROFILE_PATH = (
    Path(__file__).resolve().parent / "model_sync_profiles" / "resource_user_space.json"
)

SDK_OP_ORDER = ("list", "get", "create", "update", "delete")

CUSTOMER_OP_VALUES = frozenset(
    {
        "yes",
        "no",
        "admin-only",
        "read-only",
        "create-only",
        "platform-managed",
        "scan-generated",
        "not-supported",
    }
)

ALLOWED_ENTRY_KEYS = frozenset(
    {"limitations_short", "customer_ops", "sdk_ops", "sdk_ops_trim_exempt"}
)

# Ops omitted from SDK when customer_ops carries these values (unless sdk_ops_trim_exempt).
_CREATE_DELETE_OMIT = frozenset(
    {"no", "not-supported", "platform-managed", "scan-generated"}
)
_UPDATE_OMIT = frozenset({"no", "not-supported", "read-only"})


def profile_path() -> Path:
    return PROFILE_PATH


def load_resource_user_space() -> dict[str, dict[str, Any]]:
    """Return attr_name → profile entry."""
    raw = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"{PROFILE_PATH}: root must be an object")
    entries: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if not isinstance(key, str) or not isinstance(value, dict):
            raise RuntimeError(f"{PROFILE_PATH}: invalid entry for {key!r}")
        entries[key] = value
    return entries


def _customer_ops(entry: dict[str, Any]) -> dict[str, str]:
    ops = entry.get("customer_ops")
    if not isinstance(ops, dict):
        raise ValueError("customer_ops must be an object")
    normalized: dict[str, str] = {}
    for op in SDK_OP_ORDER:
        value = ops.get(op)
        if not isinstance(value, str) or value not in CUSTOMER_OP_VALUES:
            raise ValueError(f"customer_ops.{op} invalid: {value!r}")
        normalized[op] = value
    return normalized


def derive_sdk_ops(
    entry: dict[str, Any],
    *,
    contract_ops: list[str] | None = None,
) -> list[str]:
    """Derive SDK exposed ops from profile (explicit sdk_ops or customer_ops rules)."""
    if entry.get("sdk_ops_trim_exempt"):
        if contract_ops is None:
            raise ValueError("contract_ops required when sdk_ops_trim_exempt is true")
        return sorted(op for op in contract_ops if op in SDK_OP_ORDER)

    explicit = entry.get("sdk_ops")
    if explicit is not None:
        if not isinstance(explicit, list):
            raise ValueError("sdk_ops must be a list when set")
        return sorted(
            op for op in explicit if isinstance(op, str) and op in SDK_OP_ORDER
        )

    customer = _customer_ops(entry)
    derived: list[str] = []
    for op in SDK_OP_ORDER:
        value = customer[op]
        if op in ("create", "delete") and value in _CREATE_DELETE_OMIT:
            continue
        if op == "update" and value in _UPDATE_OMIT:
            continue
        if value in ("no", "not-supported"):
            continue
        if value == "create-only" and op != "create":
            continue
        derived.append(op)
    return derived


def validate_entry_shape(attr_name: str, entry: dict[str, Any]) -> None:
    unknown = sorted(set(entry) - ALLOWED_ENTRY_KEYS)
    if unknown:
        raise ValueError(f"{attr_name}: unknown profile keys: {', '.join(unknown)}")
    if not isinstance(entry.get("limitations_short"), str) or not entry[
        "limitations_short"
    ].strip():
        raise ValueError(f"{attr_name}: limitations_short required")
    _customer_ops(entry)
    derive_sdk_ops(entry)


def validate_complete(registry_attr_names: set[str]) -> None:
    """Every registry resource must have a profile entry; no orphan keys."""
    profile = load_resource_user_space()
    missing = sorted(registry_attr_names - set(profile))
    extra = sorted(set(profile) - registry_attr_names)
    if missing:
        raise RuntimeError(
            "resource_user_space.json missing entries: " + ", ".join(missing)
        )
    if extra:
        raise RuntimeError(
            "resource_user_space.json orphan entries (not in registry): "
            + ", ".join(extra)
        )
    for attr_name, entry in profile.items():
        validate_entry_shape(attr_name, entry)


def validate_overlay_alignment(
    merged_contract: list[dict[str, Any]],
    *,
    registry_attr_names: set[str] | None = None,
) -> None:
    """Effective supported_ops must match profile sdk_ops (post-overlay)."""
    profile = load_resource_user_space()
    if registry_attr_names is not None:
        validate_complete(registry_attr_names)

    mismatches: list[str] = []
    for row in merged_contract:
        attr_name = row.get("attr_name")
        if not isinstance(attr_name, str):
            continue
        entry = profile.get(attr_name)
        if entry is None:
            continue
        contract_ops = [
            op
            for op in row.get("supported_ops", [])
            if isinstance(op, str) and op in SDK_OP_ORDER
        ]
        expected = set(derive_sdk_ops(entry, contract_ops=contract_ops))
        actual = set(contract_ops)
        if expected != actual:
            mismatches.append(
                f"{attr_name}: overlay={sorted(actual)!r} profile={sorted(expected)!r}"
            )
    if mismatches:
        raise RuntimeError(
            "registry_overlay supported_ops mismatch vs resource_user_space.json:\n"
            + "\n".join(mismatches)
        )


def render_user_space_section(
    attr_name: str,
    entry: dict[str, Any],
    *,
    sdk_ops: list[str],
    spec_ops: dict[str, bool] | None = None,
) -> str:
    """Markdown ## User-space access block for per-resource pages."""
    customer = _customer_ops(entry)
    lines: list[str] = [
        "## User-space access",
        "",
        "Customer tenant semantics (distinct from raw OpenAPI and SDK exposure).",
        "Tenant **admin** (`SYSTEM_ROLE_ADMIN`) is the primary writer unless noted.",
        "",
        "| Operation | Customer user-space | SDK exposed |",
        "|-----------|---------------------|-------------|",
    ]
    for op in SDK_OP_ORDER:
        spec_cell = "—"
        if spec_ops is not None:
            spec_cell = "yes" if spec_ops.get(op) else "no"
        lines.append(
            f"| `{op}` | {customer[op]} | "
            f"{'yes' if op in sdk_ops else 'no'} |"
        )
    if spec_ops is not None:
        lines.extend(
            [
                "",
                "OpenAPI spec column reflects collection/item paths when available.",
            ]
        )

    trimmed = spec_ops is not None and any(
        spec_ops.get(op) and op not in sdk_ops for op in ("create", "delete", "update")
    )
    if trimmed:
        lines.extend(
            [
                "",
                "Some operations exist on the API but are not exposed on "
                f"`client.{attr_name}`.",
            ]
        )

    lines.append("")
    return "\n".join(lines)
