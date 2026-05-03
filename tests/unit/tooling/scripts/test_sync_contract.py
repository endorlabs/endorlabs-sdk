"""Unit tests for sync contract metadata builders."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from sync.contract import (
    build_facade_contract,
    build_operation_path_metadata,
    build_payload_schemas,
    build_registry_parity_report,
    build_runtime_index_metadata,
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
    import sync.contract as contract_module

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
