"""Tests for workspace collect manifest."""

from __future__ import annotations

import json

from endorlabs.workflows.estate.collect.projects import _project_row
from endorlabs.workflows.estate.contracts import (
    RESOURCE_DEPENDENCY_METADATA,
    RESOURCE_PROJECT,
    WORKSPACE_COLLECT_SCHEMA,
)
from endorlabs.workflows.estate.workspace.collect_manifest import (
    CollectManifest,
    ValidationError,
    finalize_resource,
    load_collect_manifest,
    mark_shard_complete,
    save_collect_manifest,
    validate_workspace_collect,
)
from endorlabs.workflows.estate.workspace.paths import (
    collect_manifest_path,
    ensure_workspace_layout,
    resource_path,
)


def test_collect_manifest_atomic_write(tmp_path) -> None:
    ensure_workspace_layout(tmp_path)
    manifest = CollectManifest.new("tenant.example")
    finalize_resource(
        manifest,
        RESOURCE_PROJECT,
        status="complete",
        line_count=2,
        keys=["uuid-a", "uuid-b"],
    )
    save_collect_manifest(tmp_path, manifest)
    loaded = load_collect_manifest(tmp_path)
    assert loaded is not None
    assert loaded.namespace == "tenant.example"
    assert loaded.resources[RESOURCE_PROJECT].line_count == 2


def test_validate_project_keys(tmp_path) -> None:
    ensure_workspace_layout(tmp_path)
    project_path = resource_path(tmp_path, RESOURCE_PROJECT)
    project_path.write_text(
        "\n".join(
            [
                json.dumps({"uuid": "uuid-a"}),
                json.dumps({"uuid": "uuid-b"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = CollectManifest.new("tenant.example")
    finalize_resource(
        manifest,
        RESOURCE_PROJECT,
        status="complete",
        line_count=2,
        keys=["uuid-a", "uuid-b"],
    )
    save_collect_manifest(tmp_path, manifest)
    validate_workspace_collect(tmp_path)


def test_validate_project_keys_mismatch_raises(tmp_path) -> None:
    ensure_workspace_layout(tmp_path)
    project_path = resource_path(tmp_path, RESOURCE_PROJECT)
    project_path.write_text(json.dumps({"uuid": "uuid-a"}) + "\n", encoding="utf-8")
    manifest = CollectManifest.new("tenant.example")
    finalize_resource(
        manifest,
        RESOURCE_PROJECT,
        status="complete",
        line_count=1,
        keys=["uuid-a", "uuid-b"],
    )
    save_collect_manifest(tmp_path, manifest)
    try:
        validate_workspace_collect(tmp_path)
        raised = False
    except ValidationError:
        raised = True
    assert raised


def test_shard_line_count_validation(tmp_path) -> None:
    ensure_workspace_layout(tmp_path)
    dm_path = resource_path(tmp_path, RESOURCE_DEPENDENCY_METADATA)
    dm_path.write_text(
        "\n".join(
            [
                json.dumps({"project_uuid": "p1", "row": {}}),
                json.dumps({"project_uuid": "p1", "row": {}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = CollectManifest.new("tenant.example")
    mark_shard_complete(manifest, RESOURCE_DEPENDENCY_METADATA, "p1", line_count=2)
    finalize_resource(
        manifest,
        RESOURCE_DEPENDENCY_METADATA,
        status="complete",
        line_count=2,
    )
    save_collect_manifest(tmp_path, manifest)
    validate_workspace_collect(tmp_path)


def test_manifest_schema_constant() -> None:
    manifest = CollectManifest.new("x")
    assert manifest.to_dict()["schema"] == WORKSPACE_COLLECT_SCHEMA


def test_collect_manifest_path_under_data(tmp_path) -> None:
    path = collect_manifest_path(tmp_path)
    assert path.name == "collect_manifest.json"
    assert path.parent.name == "data"


def test_ensure_workspace_layout_creates_logs_dir(tmp_path) -> None:
    from endorlabs.workflows.estate.workspace.paths import logs_dir, pull_log_path

    ensure_workspace_layout(tmp_path)
    assert logs_dir(tmp_path).is_dir()
    assert pull_log_path(tmp_path).parent.name == "logs"


def test_project_row_from_masked_dict() -> None:
    row = _project_row(
        {
            "uuid": "proj-uuid-1",
            "meta": {"name": "demo", "tags": ["t"]},
            "tenant_meta": {"namespace": "tenant.example.child"},
        },
        "tenant.example",
    )
    assert row["uuid"] == "proj-uuid-1"
    assert row["meta"]["name"] == "demo"
    assert row["tenant_meta"]["namespace"] == "tenant.example.child"
