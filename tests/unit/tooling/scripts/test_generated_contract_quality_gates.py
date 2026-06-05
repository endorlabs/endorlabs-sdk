"""Quality gates for committed model-sync registry contract."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)
_SRC_DIR = str(_REPO_ROOT / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from sync.policy import MODEL_SYNC_ENTITY_ALIASES_BY_MODEL

from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
from endorlabs.registry import RESOURCE_REGISTRY


def _contract() -> dict[str, Any]:
    if not isinstance(RUNTIME_REGISTRY_CONTRACT, dict):
        pytest.fail("RUNTIME_REGISTRY_CONTRACT must be a dict")
    return RUNTIME_REGISTRY_CONTRACT


def test_facade_contract_has_stable_resource_shape() -> None:
    """Runtime registry contract must expose stable per-resource invariant fields."""
    payload = _contract()
    resources = payload.get("resources")
    assert isinstance(resources, list) and resources
    assert payload.get("resource_count") == len(resources)

    required_keys = {
        "attr_name",
        "resource_name",
        "model_class",
        "model_class_import_path",
        "build_create_payload_fn_name",
        "build_create_payload_fn_import_path",
        "scope",
        "parent_kind",
        "supported_ops",
        "filter_kwarg_map",
        "canonical_entities",
        "accepted_canonical_entities",
        "has_tag_methods",
        "mutable_fields",
        "immutable_fields",
        "create_mode",
        "update_requires_mask",
        "identity_filter_fields",
        "workflow_flags",
        "create_payload_entities",
        "update_payload_entities",
        "create_convenience_spec_fields",
        "create_convenience_spec_required",
        "create_convenience_meta_fields",
        "create_convenience_payload_top_level_fields",
        "create_convenience_read_only_spec_fields",
        "convenience_skip_reason",
    }
    known_ops = {"list", "get", "create", "update", "delete"}
    seen_attrs: list[str] = []

    for resource in resources:
        assert isinstance(resource, dict)
        assert required_keys.issubset(resource)
        attr_name = resource["attr_name"]
        assert isinstance(attr_name, str) and attr_name
        seen_attrs.append(attr_name)

        supported_ops = resource["supported_ops"]
        assert isinstance(supported_ops, list)
        assert set(supported_ops).issubset(known_ops)
        assert len(supported_ops) == len(set(supported_ops))

        filter_map = resource["filter_kwarg_map"]
        assert isinstance(filter_map, dict)
        assert all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in filter_map.items()
        )

        for key in (
            "canonical_entities",
            "accepted_canonical_entities",
            "mutable_fields",
            "immutable_fields",
            "create_payload_entities",
            "update_payload_entities",
            "identity_filter_fields",
            "workflow_flags",
        ):
            value = resource[key]
            assert isinstance(value, list)
            assert all(isinstance(item, str) for item in value)

    assert seen_attrs == sorted(seen_attrs), "facade_contract resources must be sorted"
    assert len(seen_attrs) == len(set(seen_attrs)), "attr_name values must be unique"


def test_alias_exceptions_are_explicit_and_resolvable() -> None:
    """All alias exceptions must map to modeled resources."""
    contract = _contract()
    resources = contract.get("resources")
    assert isinstance(resources, list) and resources

    accepted_by_model: dict[str, set[str]] = {}
    for row in resources:
        if not isinstance(row, dict):
            continue
        model_name = row.get("model_class")
        accepted = row.get("accepted_canonical_entities")
        if isinstance(model_name, str) and isinstance(accepted, list):
            accepted_by_model[model_name] = {
                value for value in accepted if isinstance(value, str)
            }

    for model_name, alias in MODEL_SYNC_ENTITY_ALIASES_BY_MODEL.items():
        assert model_name in accepted_by_model, (
            f"Alias model missing from contract: {model_name}"
        )
        assert alias in accepted_by_model[model_name], (
            f"Alias {alias} missing for model {model_name}; "
            "keep alias exceptions explicit and resolvable."
        )


def test_sorted_output_ordering() -> None:
    """Generated contract resources must remain sorted and stable."""
    payload = _contract()
    resources = payload.get("resources")
    assert isinstance(resources, list) and resources
    attrs = [row.get("attr_name") for row in resources if isinstance(row, dict)]
    assert attrs == sorted(attrs)

    expected_attrs = sorted(entry.model_class.__name__ for entry in RESOURCE_REGISTRY)
    assert attrs == expected_attrs
