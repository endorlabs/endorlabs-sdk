"""Unit tests for model_sync_pr_deltas (workflow summary helpers)."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from model_sync_pr_deltas import (
    render_resource_delta_markdown,
    render_upstream_delta_markdown,
)


def test_upstream_delta_uses_operations_not_resources() -> None:
    old = {
        "operation_count": 1,
        "operations": [
            {
                "method": "get",
                "path": "/v1/a",
                "operation_id": "Svc_Old",
                "tags": ["AlphaService"],
                "request_refs": [],
                "response_refs": ["R1"],
            }
        ],
    }
    new = {
        "operation_count": 2,
        "operations": [
            {
                "method": "get",
                "path": "/v1/a",
                "operation_id": "Svc_Old",
                "tags": ["AlphaService"],
                "request_refs": [],
                "response_refs": ["R1"],
            },
            {
                "method": "post",
                "path": "/v1/b",
                "operation_id": "Svc_New",
                "tags": ["AlphaService"],
                "request_refs": [],
                "response_refs": [],
            },
        ],
    }
    lines = render_upstream_delta_markdown(old, new)
    text = "\n".join(lines)
    assert "Unique path+method endpoints (HEAD baseline): 1" in text
    assert "Unique path+method endpoints (current run): 2" in text
    assert "Added endpoint signatures: 1" in text
    assert "POST /v1/b" in text or "+ POST /v1/b" in text


def test_upstream_delta_new_tag_group() -> None:
    old = {
        "operation_count": 1,
        "operations": [
            {
                "method": "get",
                "path": "/x",
                "tags": ["A"],
            }
        ],
    }
    new = {
        "operation_count": 1,
        "operations": [
            {
                "method": "get",
                "path": "/y",
                "tags": ["B"],
            }
        ],
    }
    lines = render_upstream_delta_markdown(old, new)
    text = "\n".join(lines)
    assert "Added tag groups: 1" in text
    assert "Removed tag groups: 1" in text
    assert "New tag groups (sample): B" in text


def test_resource_delta_payload_property_shape_drift() -> None:
    old_facade = {
        "resources": [
            {
                "attr_name": "Widget",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    new_facade = dict(old_facade)
    old_payload = {
        "resources": [
            {
                "attr_name": "Widget",
                "create_payload_definitions": {
                    "WidgetBody": {
                        "properties": {
                            "spec": {"$ref": "#/definitions/v1WidgetSpec"},
                        },
                        "required": [],
                    }
                },
                "update_payload_definitions": {},
            }
        ]
    }
    new_payload = {
        "resources": [
            {
                "attr_name": "Widget",
                "create_payload_definitions": {
                    "WidgetBody": {
                        "properties": {
                            "spec": {"type": "object"},
                        },
                        "required": [],
                    }
                },
                "update_payload_definitions": {},
            }
        ]
    }
    lines = render_resource_delta_markdown(
        old_facade, new_facade, old_payload, new_payload
    )
    text = "\n".join(lines)
    assert "prop `spec`:" in text
    assert "$ref:v1WidgetSpec" in text
    assert "type:object" in text


def test_resource_delta_facade_ops_change() -> None:
    old_f = {
        "resources": [
            {
                "attr_name": "Z",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    new_f = {
        "resources": [
            {
                "attr_name": "Z",
                "supported_ops": ["get", "list"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    empty_p = {"resources": []}
    lines = render_resource_delta_markdown(old_f, new_f, empty_p, empty_p)
    text = "\n".join(lines)
    assert "Resources with operation changes: 1" in text
    assert "+ops=list" in text
    assert "**Scope (summary):**" in text
    assert "Per-resource fields" not in text


def test_resource_inventory_lists_facade_attr_names() -> None:
    """Summary always includes expandable list of attr_name (Finding, Project, …)."""
    facade = {
        "resource_count": 2,
        "resources": [
            {
                "attr_name": "Finding",
                "supported_ops": ["get", "list"],
                "mutable_fields": [],
                "immutable_fields": [],
            },
            {
                "attr_name": "Project",
                "supported_ops": ["create", "get"],
                "mutable_fields": [],
                "immutable_fields": [],
            },
        ],
    }
    empty_p = {"resources": []}
    lines = render_resource_delta_markdown(
        facade, facade, empty_p, empty_p, include_resource_inventory=True
    )
    text = "\n".join(lines)
    assert "SDK facade resources (current run, attr_name): 2" in text
    assert "Finding (facade attr_name)" in text
    assert "supported_ops: get, list" in text
    assert "Project (facade attr_name)" in text
    assert "supported_ops: create, get" in text


def test_resource_inventory_includes_payload_field_descriptions() -> None:
    """Payload property description text appears (docstring source in generated SDK)."""
    facade = {
        "resources": [
            {
                "attr_name": "Widget",
                "description": "Widget resource for tests.",
                "supported_ops": ["create"],
                "mutable_fields": ["spec.title"],
                "immutable_fields": ["uuid"],
            }
        ]
    }
    payload = {
        "resources": [
            {
                "attr_name": "Widget",
                "resource_name": "widgets",
                "create_payload_definitions": {
                    "WidgetCreateBody": {
                        "description": "Create a widget.",
                        "properties": {
                            "spec": {
                                "$ref": "#/definitions/v1WidgetSpec",
                                "description": "The widget body.",
                            },
                            "uuid": {
                                "type": "string",
                                "description": "Server-assigned id.",
                                "readOnly": True,
                            },
                        },
                        "required": ["spec"],
                        "type": "object",
                    }
                },
                "update_payload_definitions": {},
            }
        ]
    }
    lines = render_resource_delta_markdown(
        facade, facade, payload, payload, include_resource_inventory=True
    )
    text = "\n".join(lines)
    assert "Resource description (facade → class docstring source)" in text
    assert "Widget resource for tests." in text
    assert "mutable_fields (update):" in text
    assert "spec.title" in text
    assert "immutable_fields (read-only in API):" in text
    assert "uuid" in text
    assert (
        "schema description (payload / Field description source): Create a widget."
        in text
    )
    assert "spec: $ref:v1WidgetSpec | The widget body." in text
    assert "uuid: type:string [readOnly] | Server-assigned id." in text


def test_resource_summary_default_skips_full_inventory() -> None:
    """Default output is diff-only; no per-resource snapshot dump."""
    facade = {
        "resources": [
            {
                "attr_name": "OnlyOne",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    lines = render_resource_delta_markdown(
        facade, facade, {"resources": []}, {"resources": []}
    )
    text = "\n".join(lines)
    assert "SDK facade resources (current run, attr_name)" not in text
    assert "Per-resource fields" not in text
    assert "**Scope (summary):**" in text
