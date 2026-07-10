"""Unit tests for sync policy and deterministic mapping."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CODEGEN_DIR = str(_REPO_ROOT / "devtools" / "codegen")
if _CODEGEN_DIR not in sys.path:
    sys.path.insert(0, _CODEGEN_DIR)

from sync.policy import (
    build_mapping_entries,
    camel_to_snake,
    extract_spec_entities,
    filter_eligible_entities,
    modeled_resource_exception_entities,
)


def _minimal_spec() -> dict:
    return {
        "swagger": "2.0",
        "paths": {
            "/v1/namespaces/{tenant_meta.namespace}/findings": {
                "get": {
                    "operationId": "FindingServiceListFindings",
                    "tags": ["FindingService"],
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1Finding"}}
                    },
                }
            },
            "/v1/namespaces/{tenant_meta.namespace}/internal-things": {
                "get": {
                    "operationId": "InternalServiceListInternal",
                    "x-internal": True,
                    "responses": {
                        "200": {"schema": {"$ref": "#/definitions/v1InternalThing"}}
                    },
                }
            },
        },
        "definitions": {
            "v1Finding": {"type": "object", "properties": {"uuid": {"type": "string"}}},
            "v1InternalThing": {
                "type": "object",
                "properties": {"uuid": {"type": "string"}},
            },
            "FindingServiceCreateFindingBody": {
                "type": "object",
                "properties": {"meta": {"type": "object"}},
            },
        },
    }


def test_camel_to_snake_is_stable() -> None:
    assert camel_to_snake("FindingServiceCreateBody") == "finding_service_create_body"
    assert camel_to_snake("v1Finding") == "v1_finding"


def test_extract_and_filter_excludes_internal_operation_refs() -> None:
    entities = extract_spec_entities(_minimal_spec())
    eligible = filter_eligible_entities(entities)
    eligible_pairs = {(entity.entity_name, entity.source_kind) for entity in eligible}
    assert ("v1InternalThing", "operation_ref") not in eligible_pairs


def test_mapping_entries_are_sorted_and_partitioned() -> None:
    entries = build_mapping_entries(_minimal_spec())
    assert len(entries) == 1
    assert entries[0].module_path.startswith("finding")


def test_modeled_resource_exception_entities_include_aliases() -> None:
    exceptions = modeled_resource_exception_entities()
    assert "MetricServiceCreateMetricBody" in exceptions
    assert "v1Vuln" in exceptions
