"""Unit tests for OpenAPI create convenience field extraction."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools" / "codegen")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)

from sync.contract import extract_create_convenience_fields

_FIXTURE = (
    _REPO_ROOT
    / "tests"
    / "fixtures"
    / "openapi"
    / "create_convenience_vector_store_query.json"
)


def test_extract_vector_store_query_spec_fields() -> None:
    """Writable spec fields include metadata_filter; readOnly matches excluded."""
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    definitions = payload["definitions"]
    body = {"VectorStoreQueryServiceCreateVectorStoreQueryBody": definitions[
        "VectorStoreQueryServiceCreateVectorStoreQueryBody"
    ]}
    result = extract_create_convenience_fields(definitions, body)
    assert result["convenience_skip_reason"] is None
    assert result["create_convenience_spec_fields"] == [
        "vector_store_uuid",
        "query",
        "metadata_filter",
    ]
    assert result["create_convenience_spec_required"] == [
        "vector_store_uuid",
        "query",
    ]
    assert result["create_convenience_meta_fields"] == ["name"]
    assert "matches" in result["create_convenience_read_only_spec_fields"]


def test_extract_nested_spec_request_skips() -> None:
    """Nested spec.request bodies are not flat-promoted."""
    definitions = {
        "Body": {
            "type": "object",
            "properties": {
                "spec": {"$ref": "#/definitions/Spec"},
            },
            "required": ["spec"],
        },
        "Spec": {
            "type": "object",
            "properties": {
                "request": {"$ref": "#/definitions/Request"},
            },
            "required": ["request"],
        },
        "Request": {
            "type": "object",
            "properties": {
                "vector_store_uuid": {"type": "string"},
            },
        },
    }
    result = extract_create_convenience_fields(definitions, {"Body": definitions["Body"]})
    assert result["convenience_skip_reason"] == "nested_spec_request"
    assert result["create_convenience_spec_fields"] == []
