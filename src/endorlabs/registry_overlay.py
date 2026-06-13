"""Minimal policy overlay for generated runtime registry contract.

Keys in ``RESOURCE_CONTRACT_OVERLAY_BY_ATTR`` use the same ``attr_name`` as the
runtime contract: PascalCase model class names (endorctl resource kinds), e.g.
``QueryVulnerability``, not ``query_vulnerability``.
"""

from __future__ import annotations

import warnings
from typing import Any, cast

_ALLOWED_OVERRIDE_KEYS = {
    "attr_name",
    "supported_ops",
    "scope",
    "parent_kind",
    "filter_kwarg_map",
    "create_mode",
    "workflow_flags",
    "model_class_import_path",
    "build_create_payload_fn_import_path",
    "build_create_payload_fn_name",
}

# Keep this intentionally small: only explicit SDK divergences belong here.
RESOURCE_CONTRACT_OVERLAY_BY_ATTR: dict[str, dict[str, Any]] = {
    "DependencyMetadata": {
        "supported_ops": ["create", "delete", "get", "list"],
        "workflow_flags": ["project-namespace-list"],
    },
    "Finding": {
        "workflow_flags": ["project-namespace-list"],
    },
    "ScanResult": {
        "workflow_flags": ["project-namespace-list"],
    },
    "PackageVersion": {
        "workflow_flags": ["project-namespace-list"],
    },
    "IdentityProvider": {
        "model_class_import_path": (
            "endorlabs.resources.identity_provider:IdentityProvider"
        ),
        "build_create_payload_fn_import_path": (
            "endorlabs.resources.identity_provider:build_create_payload"
        ),
        "build_create_payload_fn_name": "build_create_payload",
    },
    "PackageFirewallLog": {
        "model_class_import_path": (
            "endorlabs.resources.package_firewall_log:PackageFirewallLog"
        ),
        "build_create_payload_fn_import_path": (
            "endorlabs.resources.package_firewall_log:build_create_payload"
        ),
        "build_create_payload_fn_name": "build_create_payload",
    },
    "Query": {
        "supported_ops": ["create"],
        "create_mode": "payload-only",
        "model_class_import_path": "endorlabs.resources.query:Query",
        "build_create_payload_fn_import_path": (
            "endorlabs.resources.query:build_create_payload"
        ),
        "build_create_payload_fn_name": "build_create_payload",
    },
    "QuerySimilarPackages": {
        "supported_ops": ["create"],
        "create_mode": "payload-only",
        "model_class_import_path": (
            "endorlabs.resources.query_similar_packages:QuerySimilarPackages"
        ),
        "build_create_payload_fn_import_path": (
            "endorlabs.resources.query_similar_packages:build_create_payload"
        ),
        "build_create_payload_fn_name": "build_create_payload",
    },
    "SavedQuery": {
        "model_class_import_path": "endorlabs.resources.saved_query:SavedQuery",
        "build_create_payload_fn_import_path": (
            "endorlabs.resources.saved_query:build_create_payload"
        ),
        "build_create_payload_fn_name": "build_create_payload",
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
            warnings.warn(
                f"registry_overlay: no generated contract row for {attr_name!r}; "
                "overlay entry skipped",
                UserWarning,
                stacklevel=2,
            )
            continue
        for key, value in override.items():
            if key in _ALLOWED_OVERRIDE_KEYS:
                by_attr[attr_name][key] = value
    return [by_attr[attr_name] for attr_name in sorted(by_attr)]
