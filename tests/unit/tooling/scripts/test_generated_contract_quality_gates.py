"""Quality gates for generated model-sync contract artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)

from sync.policy import MODEL_SYNC_ENTITY_ALIASES_BY_MODEL

from endorlabs.registry import RESOURCE_REGISTRY

_MODEL_SYNC_ROOT = _REPO_ROOT / "workspace" / "model-sync" / "custom_mapping"
_FACADE_CONTRACT_PATH = _MODEL_SYNC_ROOT / "facade_contract.json"
_PARITY_REPORT_PATH = _MODEL_SYNC_ROOT / "mapping" / "registry_parity_report.json"
_OP_METADATA_PATH = _MODEL_SYNC_ROOT / "mapping" / "operation_path_metadata.json"
_PAYLOAD_SCHEMAS_PATH = _MODEL_SYNC_ROOT / "mapping" / "payload_schemas.json"
_ARTIFACTS_MANIFEST_PATH = _MODEL_SYNC_ROOT / "artifacts_manifest.json"
_RUNTIME_INDEX_PATH = _MODEL_SYNC_ROOT / "mapping" / "runtime_index.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        if os.getenv("CI"):
            pytest.fail(f"Generated artifact missing in CI ({path})")
        pytest.skip(f"Generated artifact missing ({path})")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        pytest.fail(f"Artifact root must be object: {path}")
    return payload


def test_facade_contract_has_stable_resource_shape() -> None:
    """Facade contract must expose stable per-resource invariant fields."""
    payload = _load_json(_FACADE_CONTRACT_PATH)
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
    }
    known_ops = {"list", "get", "create", "update", "delete"}
    seen_attrs: list[str] = []

    for resource in resources:
        assert isinstance(resource, dict)
        assert required_keys.issubset(resource)

        attr_name = resource["attr_name"]
        assert isinstance(attr_name, str) and attr_name
        seen_attrs.append(attr_name)
        assert isinstance(resource["model_class_import_path"], str)

        assert resource["scope"] in {"tenant", "oss"}
        assert resource["parent_kind"] is None or isinstance(
            resource["parent_kind"], str
        )
        assert isinstance(resource["has_tag_methods"], bool)
        assert resource["create_mode"] in {"both", "payload-only", "unsupported"}
        assert isinstance(resource["update_requires_mask"], bool)

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


def test_registry_parity_report_contract_is_well_formed() -> None:
    """Parity report must be structured and indicate no missing registry mappings."""
    payload = _load_json(_PARITY_REPORT_PATH)
    assert payload.get("status") in {"pass", "fail"}
    for key in (
        "missing_in_mapping",
        "mapping_without_registry_match",
        "alias_matches",
    ):
        assert isinstance(payload.get(key), list)
    assert payload.get("status") == "pass"
    assert payload.get("missing_in_mapping") == []


def test_operation_metadata_has_unique_path_method_pairs() -> None:
    """Operation metadata must have stable shape and unique path+method rows."""
    payload = _load_json(_OP_METADATA_PATH)
    operations = payload.get("operations")
    assert isinstance(operations, list) and operations
    assert payload.get("operation_count") == len(operations)

    required_keys = {
        "path",
        "method",
        "operation_id",
        "tags",
        "x_internal",
        "request_refs",
        "response_refs",
    }
    seen_pairs: set[tuple[str, str]] = set()

    for operation in operations:
        assert isinstance(operation, dict)
        assert required_keys.issubset(operation)
        path = operation["path"]
        method = operation["method"]
        assert isinstance(path, str) and path.startswith("/")
        assert isinstance(method, str) and method == method.lower()
        pair = (path, method)
        assert pair not in seen_pairs
        seen_pairs.add(pair)

        assert operation["operation_id"] is None or isinstance(
            operation["operation_id"], str
        )
        assert isinstance(operation["x_internal"], bool)
        assert isinstance(operation["tags"], list)
        assert all(isinstance(tag, str) for tag in operation["tags"])
        for key in ("request_refs", "response_refs"):
            value = operation[key]
            assert isinstance(value, list)
            assert all(isinstance(ref, str) for ref in value)


def test_payload_schema_metadata_has_expected_keys() -> None:
    """Payload schema catalog must be complete per-resource metadata."""
    payload = _load_json(_PAYLOAD_SCHEMAS_PATH)
    resources = payload.get("resources")
    assert isinstance(resources, list) and resources
    assert payload.get("resource_count") == len(resources)

    required_keys = {
        "attr_name",
        "resource_name",
        "create_payload_entities",
        "update_payload_entities",
        "create_payload_definitions",
        "update_payload_definitions",
    }
    for resource in resources:
        assert isinstance(resource, dict)
        assert required_keys.issubset(resource)
        assert isinstance(resource["attr_name"], str) and resource["attr_name"]
        assert isinstance(resource["resource_name"], str) and resource["resource_name"]
        for key in ("create_payload_entities", "update_payload_entities"):
            value = resource[key]
            assert isinstance(value, list)
            assert all(isinstance(item, str) for item in value)
        for key in ("create_payload_definitions", "update_payload_definitions"):
            assert isinstance(resource[key], dict)


def test_x_internal_policy_consistency() -> None:
    """x-internal policy should be stable per operationId."""
    payload = _load_json(_OP_METADATA_PATH)
    operations = payload.get("operations")
    assert isinstance(operations, list) and operations

    op_internal_flags: dict[str, bool] = {}
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        operation_id = operation.get("operation_id")
        x_internal = operation.get("x_internal")
        if not isinstance(operation_id, str) or not operation_id:
            continue
        if not isinstance(x_internal, bool):
            continue
        existing = op_internal_flags.get(operation_id)
        if existing is not None:
            assert existing == x_internal, (
                f"operationId {operation_id} has conflicting x-internal flags "
                f"({existing} vs {x_internal})"
            )
        op_internal_flags[operation_id] = x_internal


def test_alias_exceptions_are_explicit_and_resolvable() -> None:
    """All alias exceptions must map to modeled resources."""
    contract = _load_json(_FACADE_CONTRACT_PATH)
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


def test_sync_two_run_hash_stability() -> None:
    """Manifest overall hash must match deterministic recomputation."""
    payload = _load_json(_ARTIFACTS_MANIFEST_PATH)
    files = payload.get("files")
    assert isinstance(files, list)
    manifest_bytes = json.dumps(files, sort_keys=True).encode("utf-8")
    expected_sha = hashlib.sha256(manifest_bytes).hexdigest()
    assert payload.get("overall_sha256") == expected_sha


def test_sorted_output_ordering() -> None:
    """Generated contract resources must remain sorted and stable."""
    payload = _load_json(_FACADE_CONTRACT_PATH)
    resources = payload.get("resources")
    assert isinstance(resources, list) and resources
    attrs = [row.get("attr_name") for row in resources if isinstance(row, dict)]
    assert attrs == sorted(attrs)

    expected_attrs = sorted(entry.attr_name for entry in RESOURCE_REGISTRY)
    assert attrs == expected_attrs


def test_runtime_index_has_model_and_builder_imports() -> None:
    """Runtime index should provide deterministic import maps."""
    payload = _load_json(_RUNTIME_INDEX_PATH)
    model_index = payload.get("model_class_import_by_name")
    builder_index = payload.get("create_builder_import_by_name")
    mutability_by_resource = payload.get("mutability_by_resource")
    capability_by_resource = payload.get("capability_by_resource")
    assert isinstance(model_index, dict) and model_index
    assert isinstance(builder_index, dict)
    assert isinstance(mutability_by_resource, dict)
    assert isinstance(capability_by_resource, dict)
    for key, value in model_index.items():
        assert isinstance(key, str)
        assert isinstance(value, str)
        assert ":" in value
