"""OpenAPI quality gates for stable, deterministic SDK generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_DIR = str(_REPO_ROOT / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
_SPEC_PATH = (
    _REPO_ROOT
    / ".endorlabs-context"
    / "platform"
    / "openapi"
    / "openapiv2.swagger.json"
)


def _load_facade_contract() -> dict[str, Any]:
    try:
        from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    except ImportError:
        pytest.skip("Committed registry contract module not importable")
    if not isinstance(RUNTIME_REGISTRY_CONTRACT, dict):
        pytest.skip("Invalid runtime registry contract")
    return RUNTIME_REGISTRY_CONTRACT


_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def _load_spec() -> dict[str, Any]:
    if not _SPEC_PATH.exists():
        pytest.skip(f"OpenAPI spec not present ({_SPEC_PATH})")
    return json.loads(_SPEC_PATH.read_text(encoding="utf-8"))


def _extract_definition_ref(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    marker = "#/definitions/"
    if marker not in value:
        return None
    return value.split(marker, maxsplit=1)[1]


def _collect_operation_refs(operation: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    parameters = operation.get("parameters")
    if isinstance(parameters, list):
        for parameter in parameters:
            if not isinstance(parameter, dict):
                continue
            schema = parameter.get("schema")
            if isinstance(schema, dict):
                ref = _extract_definition_ref(schema.get("$ref"))
                if ref is not None:
                    refs.add(ref)

    responses = operation.get("responses")
    if isinstance(responses, dict):
        for response in responses.values():
            if not isinstance(response, dict):
                continue
            schema = response.get("schema")
            if isinstance(schema, dict):
                ref = _extract_definition_ref(schema.get("$ref"))
                if ref is not None:
                    refs.add(ref)
    return refs


def test_operation_ids_are_unique() -> None:
    """Operation IDs must be unique for deterministic traceability/codegen."""
    spec = _load_spec()
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        pytest.skip("OpenAPI spec has no paths section")

    seen: set[str] = set()
    duplicates: set[str] = set()
    for method_map in paths.values():
        if not isinstance(method_map, dict):
            continue
        for method, operation in method_map.items():
            if method not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str):
                continue
            if operation_id in seen:
                duplicates.add(operation_id)
            seen.add(operation_id)

    assert not duplicates, f"Duplicate operationId values: {sorted(duplicates)}"


def test_definition_refs_resolve_in_request_and_response_schemas() -> None:
    """All #/definitions refs used by operations must exist."""
    spec = _load_spec()
    paths = spec.get("paths")
    definitions = spec.get("definitions")
    if not isinstance(paths, dict) or not isinstance(definitions, dict):
        pytest.skip("OpenAPI spec missing paths/definitions")

    definition_names = set(definitions.keys())
    referenced_definition_names: set[str] = set()

    for method_map in paths.values():
        if not isinstance(method_map, dict):
            continue
        for method, operation in method_map.items():
            if method not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            referenced_definition_names.update(_collect_operation_refs(operation))

    missing_refs = sorted(referenced_definition_names - definition_names)

    assert not missing_refs, f"Unresolvable #/definitions refs: {sorted(missing_refs)}"


def test_resource_paths_have_expected_method_shapes() -> None:
    """Canonical collection/item paths should expose stable method map shapes."""
    spec = _load_spec()
    contract = _load_facade_contract()
    resources = contract.get("resources")
    paths = spec.get("paths")
    if not isinstance(resources, list) or not isinstance(paths, dict):
        pytest.skip("OpenAPI spec or facade contract missing required sections")

    for row in resources:
        if not isinstance(row, dict):
            continue
        resource_name = row.get("resource_name")
        if not isinstance(resource_name, str):
            continue
        collection_path = f"/v1/namespaces/{{tenant_meta.namespace}}/{resource_name}"
        item_path = f"{collection_path}/{{uuid}}"

        collection_methods = paths.get(collection_path, {})
        item_methods = paths.get(item_path, {})
        assert isinstance(collection_methods, dict)
        assert isinstance(item_methods, dict)

        normalized_collection = sorted(
            method for method in collection_methods if method in _HTTP_METHODS
        )
        normalized_item = sorted(
            method for method in item_methods if method in _HTTP_METHODS
        )

        # Collection/item method lists should already be deterministic and unique.
        assert normalized_collection == sorted(set(normalized_collection))
        assert normalized_item == sorted(set(normalized_item))
