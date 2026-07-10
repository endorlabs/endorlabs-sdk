"""Unit tests for sync contract metadata builders."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest  # noqa: TC002

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools" / "codegen")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)

from sync.contract import (
    build_facade_contract,
    build_operation_path_metadata,
    build_payload_schemas,
    build_registry_parity_report,
    build_runtime_index_metadata,
    infer_resource_scope,
    validate_contract_artifacts,
)
from sync.policy import MappingEntry


def _spec() -> dict:
    return {
        "swagger": "2.0",
        "paths": {
            "/v1/namespaces/{object.tenant_meta.namespace}/findings": {
                "post": {
                    "operationId": "FindingServiceCreateFindingByObjectNamespace",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "schema": {"$ref": "#/definitions/FindingCreateBody"},
                        }
                    ],
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1Finding"}}
                    },
                },
                "patch": {
                    "operationId": "FindingServiceUpdateFindingByObjectNamespace",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "object": {
                                        "$ref": "#/definitions/FindingUpdateBody"
                                    },
                                    "request": {
                                        "$ref": "#/definitions/UpdateRequest",
                                    },
                                },
                            },
                        }
                    ],
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1Finding"}}
                    },
                },
            },
            "/v1/namespaces/{tenant_meta.namespace}/findings": {
                "post": {
                    "operationId": "FindingServiceCreateFinding",
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "schema": {
                                "allOf": [
                                    {"$ref": "#/definitions/FindingCreateBody"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "details": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/definitions/FindingCreateDetails"
                                                },
                                            }
                                        },
                                    },
                                ]
                            },
                        }
                    ],
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1Finding"}}
                    },
                }
            },
            "/v1/namespaces/{tenant_meta.namespace}/findings/{uuid}": {
                "patch": {
                    "operationId": "FindingServiceUpdateFinding",
                    "x-internal": False,
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "schema": {"$ref": "#/definitions/FindingUpdateBody"},
                        }
                    ],
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1Finding"}}
                    },
                }
            },
        },
        "definitions": {
            "v1Finding": {"type": "object"},
            "FindingCreateBody": {"type": "object"},
            "FindingCreateDetails": {"type": "object"},
            "FindingUpdateBody": {"type": "object"},
            "UpdateRequest": {"type": "object"},
        },
    }


def test_build_operation_path_metadata_extracts_refs() -> None:
    metadata = build_operation_path_metadata(_spec())
    assert metadata["operation_count"] == 4
    operations = metadata["operations"]
    create_ops = [
        op
        for op in operations
        if op["path"].endswith("/findings") and op["method"] == "post"
    ]
    assert create_ops
    assert any("FindingCreateDetails" in op["request_refs"] for op in create_ops)
    assert all(op["response_refs"] for op in create_ops)


def test_build_payload_schemas_and_contract(monkeypatch) -> None:
    fake_registry = [
        SimpleNamespace(
            attr_name="finding",
            resource_name="findings",
            model_class=type("Finding", (), {}),
            supported_ops=frozenset({"list", "get", "create", "update"}),
            filter_kwarg_map={"name": "meta.name"},
            parent_kind=None,
            scope=None,
        )
    ]
    contract_module = sys.modules[build_facade_contract.__module__]

    monkeypatch.setattr(contract_module, "RESOURCE_REGISTRY", fake_registry)
    mapping_entries = [
        MappingEntry(
            entity_name="v1Finding",
            module_path="finding_service",
            source_kind="definition",
            source_key="v1Finding",
            operation_id=None,
        )
    ]

    operation_metadata = build_operation_path_metadata(_spec())
    payload = build_payload_schemas(spec=_spec(), operation_metadata=operation_metadata)
    contract = build_facade_contract(
        mapping_entries=mapping_entries,
        payload_schemas=payload,
        operation_metadata=operation_metadata,
    )
    runtime_index = build_runtime_index_metadata(contract)
    parity = build_registry_parity_report(
        mapping_entries=mapping_entries,
        facade_contract=contract,
    )
    errors = validate_contract_artifacts(
        facade_contract=contract,
        registry_parity_report=parity,
        operation_path_metadata=operation_metadata,
        payload_schemas=payload,
    )

    assert contract["resource_count"] == 1
    resource_row = contract["resources"][0]
    assert resource_row["model_class_import_path"].endswith(":Finding")
    assert isinstance(resource_row["mutable_fields"], list)
    assert isinstance(resource_row["immutable_fields"], list)
    assert resource_row["create_mode"] in {"both", "payload-only", "unsupported"}
    assert isinstance(resource_row["update_requires_mask"], bool)
    assert isinstance(resource_row["identity_filter_fields"], list)
    assert isinstance(resource_row["workflow_flags"], list)
    assert "FindingCreateBody" in resource_row["create_payload_entities"]
    assert "FindingUpdateBody" in resource_row["update_payload_entities"]
    assert "UpdateRequest" in resource_row["update_payload_entities"]
    assert runtime_index["model_class_import_by_name"]["Finding"].endswith(":Finding")
    assert isinstance(runtime_index["capability_by_resource"], dict)
    assert parity["status"] in {"pass", "fail"}
    assert not errors


def test_validate_contract_artifacts_fails_on_parity_status_fail() -> None:
    facade_contract = {
        "resources": [
            {
                "attr_name": "Example",
                "resource_name": "examples",
                "model_class": "Example",
                "model_class_import_path": "endorlabs.resources.example:Example",
                "build_create_payload_fn_name": None,
                "build_create_payload_fn_import_path": None,
                "scope": None,
                "parent_kind": None,
                "supported_ops": ["list"],
                "filter_kwarg_map": {},
                "canonical_entities": [],
                "accepted_canonical_entities": [],
                "has_tag_methods": False,
                "mutable_fields": [],
                "immutable_fields": [],
                "create_mode": "unsupported",
                "update_requires_mask": False,
                "identity_filter_fields": [],
                "workflow_flags": [],
                "create_payload_entities": [],
                "update_payload_entities": [],
                "create_convenience_spec_fields": [],
                "create_convenience_spec_required": [],
                "create_convenience_meta_fields": [],
                "create_convenience_payload_top_level_fields": [],
                "create_convenience_read_only_spec_fields": [],
                "convenience_skip_reason": "test",
            }
        ],
        "resource_count": 1,
    }
    registry_parity_report = {
        "status": "fail",
        "missing_in_mapping": ["Example"],
        "mapping_without_registry_match": [],
        "alias_matches": [],
    }
    operation_path_metadata = {
        "operations": [
            {
                "path": "/v1/namespaces/{tenant_meta.namespace}/examples",
                "method": "get",
                "operation_id": "ExampleServiceList",
                "tags": [],
                "x_internal": False,
                "request_refs": [],
                "response_refs": [],
            }
        ]
    }
    payload_schemas = {
        "resources": [
            {
                "attr_name": "Example",
                "create_definitions": {},
                "update_definitions": {},
                "create_convenience_spec_fields": [],
                "create_convenience_spec_required": [],
                "create_convenience_meta_fields": [],
                "create_convenience_payload_top_level_fields": [],
                "create_convenience_read_only_spec_fields": [],
                "convenience_skip_reason": "test",
            }
        ]
    }
    errors = validate_contract_artifacts(
        facade_contract=facade_contract,
        registry_parity_report=registry_parity_report,
        operation_path_metadata=operation_path_metadata,
        payload_schemas=payload_schemas,
    )
    assert any("registry parity failed" in error for error in errors)


def test_infer_resource_scope_from_openapi_paths() -> None:
    spec = {
        "paths": {
            "/v1/namespaces/{tenant_meta.namespace}/dependency-metadata": {"get": {}},
            "/v1/namespaces/{tenant_meta.namespace}/dependency-metadata/{uuid}": {
                "get": {}
            },
            "/v1/namespaces/{object.tenant_meta.namespace}/dependency-metadata": {
                "post": {}
            },
        }
    }
    metadata = build_operation_path_metadata(spec)
    assert infer_resource_scope("dependency-metadata", metadata) == "tenant"


def test_infer_resource_scope_oss_literal_paths() -> None:
    spec = {
        "paths": {
            "/v1/namespaces/oss/malware": {"get": {}},
            "/v1/namespaces/oss/malware/{uuid}": {"get": {}},
        }
    }
    metadata = build_operation_path_metadata(spec)
    assert infer_resource_scope("malware", metadata) == "oss"


def test_build_facade_contract_uses_openapi_scope_not_runtime_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_registry = [
        SimpleNamespace(
            attr_name="dependency_metadata",
            resource_name="dependency-metadata",
            model_class=type("DependencyMetadata", (), {}),
            supported_ops=frozenset({"list", "get"}),
            filter_kwarg_map={},
            parent_kind=None,
            scope="oss",
        )
    ]
    contract_module = sys.modules[build_facade_contract.__module__]

    monkeypatch.setattr(contract_module, "RESOURCE_REGISTRY", fake_registry)
    spec = {
        "paths": {
            "/v1/namespaces/{tenant_meta.namespace}/dependency-metadata": {"get": {}},
        }
    }
    operation_metadata = build_operation_path_metadata(spec)
    contract = build_facade_contract(
        mapping_entries=[],
        payload_schemas={"resources": []},
        operation_metadata=operation_metadata,
    )
    row = next(
        r for r in contract["resources"] if r["resource_name"] == "dependency-metadata"
    )
    assert row["scope"] == "tenant"
