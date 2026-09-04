"""Tests for resource_user_space profile loader and overlay alignment."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEVTOOLS = _REPO_ROOT / "devtools" / "codegen"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT  # noqa: E402
from endorlabs.registry import RESOURCE_REGISTRY  # noqa: E402
from endorlabs.registry_overlay import merge_generated_contract_with_overlay  # noqa: E402
from resource_user_space import (  # noqa: E402
    CUSTOMER_OP_VALUES,
    derive_sdk_ops,
    load_resource_user_space,
    validate_complete,
    validate_overlay_alignment,
)


def test_profile_covers_all_registry_resources() -> None:
    names = {entry.attr_name for entry in RESOURCE_REGISTRY}
    validate_complete(names)
    profile = load_resource_user_space()
    assert len(profile) == len(names) == 46


def test_profile_customer_ops_use_known_enums() -> None:
    profile = load_resource_user_space()
    for attr_name, entry in profile.items():
        ops = entry.get("customer_ops")
        assert isinstance(ops, dict), attr_name
        for op, value in ops.items():
            assert value in CUSTOMER_OP_VALUES, f"{attr_name}.{op}={value!r}"


def test_overlay_matches_profile_sdk_ops() -> None:
    names = {entry.attr_name for entry in RESOURCE_REGISTRY}
    merged = merge_generated_contract_with_overlay(
        RUNTIME_REGISTRY_CONTRACT["resources"]
    )
    validate_overlay_alignment(merged, registry_attr_names=names)


def test_system_config_derived_sdk_ops() -> None:
    profile = load_resource_user_space()
    entry = profile["SystemConfig"]
    assert derive_sdk_ops(entry) == ["get", "list", "update"]


def test_profile_rejects_unknown_keys() -> None:
    from resource_user_space import validate_entry_shape

    with pytest.raises(ValueError, match="unknown profile keys"):
        validate_entry_shape(
            "Example",
            {
                "limitations_short": "Example",
                "customer_ops": {
                    "list": "yes",
                    "get": "yes",
                    "create": "no",
                    "update": "no",
                    "delete": "no",
                },
                "recommended_workflow": "stale field",
            },
        )


def test_malware_profile_read_only_ops() -> None:
    profile = load_resource_user_space()
    entry = profile["Malware"]
    assert entry["limitations_short"] == "OSS-scoped malware catalog"
    assert set(derive_sdk_ops(entry)) == {"get", "list"}
