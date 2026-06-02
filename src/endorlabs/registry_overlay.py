"""Minimal policy overlay for generated runtime registry contract.

Keys in ``RESOURCE_CONTRACT_OVERLAY_BY_ATTR`` use the same ``attr_name`` as the
runtime contract: PascalCase model class names (endorctl resource kinds), e.g.
``QueryVulnerability``, not ``query_vulnerability``.
"""

from __future__ import annotations

from typing import Any, cast

_ALLOWED_OVERRIDE_KEYS = {
    "attr_name",
    "supported_ops",
    "scope",
    "parent_kind",
    "filter_kwarg_map",
    "create_mode",
}

# Keep this intentionally small: only explicit SDK divergences belong here.
RESOURCE_CONTRACT_OVERLAY_BY_ATTR: dict[str, dict[str, Any]] = {
    # endorctl --resource PackageFirewallLog; generated model keeps V1 prefix.
    "V1PackageFirewallLog": {
        "attr_name": "PackageFirewallLog",
    },
    # OpenAPI exposes POST-only query endpoints (no collection GET/list).
    "V1Query": {
        "supported_ops": ["create"],
        "create_mode": "payload-only",
    },
    "V1QuerySimilarPackages": {
        "supported_ops": ["create"],
        "create_mode": "payload-only",
    },
    # Tenant-scoped importer rows: list/get use the customer namespace path
    # (see tests/unit/client/test_client_facade.py).
    "DependencyMetadata": {
        "supported_ops": ["create", "delete", "get", "list"],
    },
}


def merge_generated_contract_with_overlay(
    generated_resources: list[Any],
) -> list[dict[str, Any]]:
    """Merge generated resource contract with explicit per-resource overrides."""
    by_attr: dict[str, dict[str, Any]] = {}
    for item in generated_resources:
        if not isinstance(item, dict):
            continue
        item_dict = cast("dict[str, Any]", item)
        attr_name = item_dict.get("attr_name")
        if isinstance(attr_name, str):
            by_attr[attr_name] = dict(item_dict)
    for attr_name, override in RESOURCE_CONTRACT_OVERLAY_BY_ATTR.items():
        if attr_name not in by_attr:
            continue
        for key, value in override.items():
            if key in _ALLOWED_OVERRIDE_KEYS:
                by_attr[attr_name][key] = value
    return [by_attr[attr_name] for attr_name in sorted(by_attr)]
