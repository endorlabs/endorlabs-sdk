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
    build_resource_delta_structured,
    build_upstream_delta_structured,
    render_provenance_delta_markdown,
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
    assert "Unique path+method endpoints (git HEAD): 1" in text
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
    assert "(~)" in text
    assert "create WidgetBody spec:" in text
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
    assert "|- (+) supported_ops: list" in text
    assert "Z" in text
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
    assert "Full field inventory (opt-in)" in text
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
    assert "Full field inventory (opt-in)" in text
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


def test_upstream_maintainer_readout_when_no_deltas() -> None:
    meta = {
        "operation_count": 1,
        "operations": [
            {"method": "get", "path": "/x", "tags": ["T"], "request_refs": []}
        ],
    }
    lines = render_upstream_delta_markdown(meta, meta, baseline_ref="HEAD")
    text = "\n".join(lines)
    assert "#### Maintainer readout" in text
    assert "Nothing vs `git HEAD`" in text


def test_provenance_delta_lists_field_changes() -> None:
    old = {
        "endorctl_version": "1.0.0",
        "generated_at_utc": "2026-01-01T00:00:00Z",
        "spec_sha256": "aa" * 32,
        "spec_path": "/old/path.json",
    }
    new = {
        **old,
        "generated_at_utc": "2026-01-02T00:00:00Z",
        "spec_path": "/new/path.json",
    }
    lines = render_provenance_delta_markdown(old, new, baseline_ref="HEAD")
    text = "\n".join(lines)
    assert "### Provenance delta" in text
    assert "`generated_at_utc`: **changed**" in text
    assert "`spec_sha256`: **unchanged**" in text
    assert "`endorctl_version`: **unchanged**" in text


def test_resource_maintainer_readout_when_no_deltas() -> None:
    facade = {
        "resources": [
            {
                "attr_name": "X",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    empty_p = {"resources": []}
    lines = render_resource_delta_markdown(
        facade, facade, empty_p, empty_p, baseline_ref="main"
    )
    text = "\n".join(lines)
    assert "git main" in text
    assert "#### Maintainer readout" in text
    assert "provenance.json" in text


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
    assert "No resource façade or payload deltas" in text


def test_build_upstream_delta_structured_no_deltas() -> None:
    meta = {
        "operations": [
            {
                "method": "get",
                "path": "/x",
                "operation_id": "ReadX",
                "tags": ["TagX"],
                "request_refs": [],
                "response_refs": ["R"],
            }
        ]
    }
    data = build_upstream_delta_structured(meta, meta)
    assert data["has_upstream_delta"] is False
    assert data["added_endpoints"] == []
    assert data["removed_endpoints"] == []
    assert data["added_tags"] == []
    assert data["removed_tags"] == []
    assert data["signature_drift"] == []


def test_build_resource_delta_structured_payload_and_ops_and_fields() -> None:
    old_facade = {
        "resources": [
            {
                "attr_name": "Widget",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": ["uuid"],
            }
        ]
    }
    new_facade = {
        "resources": [
            {
                "attr_name": "Widget",
                "supported_ops": ["get", "update"],
                "mutable_fields": ["spec.title"],
                "immutable_fields": [],
            }
        ]
    }
    old_payload = {
        "resources": [
            {
                "attr_name": "Widget",
                "create_payload_definitions": {
                    "WidgetBody": {
                        "properties": {"spec": {"$ref": "#/definitions/v1WidgetSpec"}},
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
                        "properties": {"spec": {"type": "object"}},
                        "required": ["spec"],
                    }
                },
                "update_payload_definitions": {},
            }
        ]
    }
    data = build_resource_delta_structured(
        old_facade,
        new_facade,
        old_payload,
        new_payload,
    )
    assert data["has_resource_delta"] is True
    assert data["changed_resources"] == ["Widget"]
    assert "Widget" in data["resource_op_changes"]
    assert "Widget" in data["resource_field_changes"]
    assert "Widget" in data["resource_payload_changes"]
    assert any("+ops=update" in x for x in data["resource_op_changes"]["Widget"])
    assert any(
        "+mutable=spec.title" in x for x in data["resource_field_changes"]["Widget"]
    )
    assert any("prop `spec`" in x for x in data["resource_payload_changes"]["Widget"])


def test_resource_delta_tree_resource_added_and_removed() -> None:
    old_f = {
        "resources": [
            {
                "attr_name": "Gone",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    new_f = {
        "resources": [
            {
                "attr_name": "Nova",
                "supported_ops": ["get"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    empty_p = {"resources": []}
    lines = render_resource_delta_markdown(old_f, new_f, empty_p, empty_p)
    text = "\n".join(lines)
    assert "|- (+) resource [added to SDK façade]" in text
    assert "|- (-) resource [removed from SDK façade]" in text
    assert "Gone" in text
    assert "Nova" in text


def test_resource_delta_tree_payload_add_property() -> None:
    facade = {
        "resources": [
            {
                "attr_name": "Widget",
                "supported_ops": ["create"],
                "mutable_fields": [],
                "immutable_fields": [],
            }
        ]
    }
    old_payload = {
        "resources": [
            {
                "attr_name": "Widget",
                "create_payload_definitions": {
                    "WidgetBody": {
                        "properties": {},
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
                            "title": {
                                "type": "string",
                                "description": "Widget title from API spec.",
                            }
                        },
                        "required": [],
                    }
                },
                "update_payload_definitions": {},
            }
        ]
    }
    lines = render_resource_delta_markdown(facade, facade, old_payload, new_payload)
    text = "\n".join(lines)
    assert "|- (+) create WidgetBody title" in text
    assert "[type:string]" in text
    assert "Widget title from API spec." in text
