"""Tests for finding collect stamping project_uuid for shard validation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import Mock

from endorlabs.workflows.estate.collect.runner import _collect_sharded_resource

if TYPE_CHECKING:
    from endorlabs.workflows.estate.collect.shards import ParentShard
from endorlabs.workflows.estate.contracts import RESOURCE_FINDING, RESOURCE_PROJECT
from endorlabs.workflows.estate.workspace.collect_manifest import (
    CollectManifest,
    finalize_resource,
    save_collect_manifest,
    validate_workspace_collect,
)
from endorlabs.workflows.estate.workspace.paths import (
    ensure_workspace_layout,
    resource_path,
)


def test_collect_finding_stamps_project_uuid_for_shard_validation(
    tmp_path, monkeypatch
) -> None:
    ensure_workspace_layout(tmp_path)
    project_path = resource_path(tmp_path, RESOURCE_PROJECT)
    project_path.write_text(
        json.dumps(
            {
                "uuid": "p1",
                "meta": {"name": "demo"},
                "tenant_meta": {"namespace": "tenant.child"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = CollectManifest.new("tenant")
    finalize_resource(
        manifest,
        RESOURCE_PROJECT,
        status="complete",
        line_count=1,
        keys=["p1"],
    )
    save_collect_manifest(tmp_path, manifest)

    def _mock_fetch(
        _client: Mock,
        shard: ParentShard,
        *,
        max_pages: int | None,
        page_size: int,
    ) -> tuple[list[dict], str | None]:
        _ = max_pages, page_size
        return [{"spec": {"level": "FINDING_LEVEL_HIGH"}}], None

    monkeypatch.setattr(
        "endorlabs.workflows.estate.collect.runner._fetch_findings_for_shard",
        _mock_fetch,
    )

    count = _collect_sharded_resource(
        Mock(),
        namespace="tenant",
        workspace_root=tmp_path,
        manifest=manifest,
        resource_id=RESOURCE_FINDING,
        max_workers=1,
        max_pages=None,
        page_size=500,
        resume=False,
        preflight=False,
        validate_counts=False,
        filter_fn=lambda _shard: "filter",
        facade_attr="Finding",
        record_builder=lambda rows, shard: [
            {**row, "project_uuid": shard.key} for row in (rows or [])
        ],
    )
    assert count == 1

    finding_path = resource_path(tmp_path, RESOURCE_FINDING)
    row = json.loads(finding_path.read_text(encoding="utf-8").strip())
    assert row["project_uuid"] == "p1"
    assert row["spec"]["level"] == "FINDING_LEVEL_HIGH"

    validate_workspace_collect(tmp_path)
