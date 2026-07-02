"""Tests for finding collect stamping project_uuid for shard validation."""

from __future__ import annotations

import json
import threading
import time
from typing import TYPE_CHECKING
from unittest.mock import Mock

if TYPE_CHECKING:
    from endorlabs.tools.list_sharding import ParentShard
from endorlabs.workflows.estate.collect.runner import _collect_sharded_resource
from endorlabs.workflows.estate.contracts import (
    RESOURCE_DEPENDENCY_METADATA,
    RESOURCE_FINDING,
    RESOURCE_PROJECT,
)
from endorlabs.workflows.estate.workspace.collect_manifest import (
    CollectManifest,
    finalize_resource,
    load_collect_manifest,
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


def test_collect_sharded_resource_persists_manifest_before_all_shards_finish(
    tmp_path,
) -> None:
    ensure_workspace_layout(tmp_path)
    project_path = resource_path(tmp_path, RESOURCE_PROJECT)
    for pid in ("p-fast", "p-slow"):
        with project_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "uuid": pid,
                        "meta": {"name": pid},
                        "tenant_meta": {"namespace": "tenant.child"},
                    }
                )
                + "\n"
            )

    manifest = CollectManifest.new("tenant")
    finalize_resource(
        manifest,
        RESOURCE_PROJECT,
        status="complete",
        line_count=2,
        keys=["p-fast", "p-slow"],
    )
    save_collect_manifest(tmp_path, manifest)

    release_slow = threading.Event()

    def _mock_list(
        *,
        filter: str,  # noqa: A002
        namespace: str,
        mask: str,
        max_pages: int | None,
        page_size: int,
    ) -> list[dict[str, str]]:
        _ = namespace, mask, max_pages, page_size
        if "p-slow" in filter:
            release_slow.wait(timeout=5.0)
        return [{"uuid": "dm-row"}]

    client = Mock()
    client.DependencyMetadata.list = _mock_list

    def _collect_in_thread() -> None:
        _collect_sharded_resource(
            client,
            namespace="tenant",
            workspace_root=tmp_path,
            manifest=manifest,
            resource_id=RESOURCE_DEPENDENCY_METADATA,
            max_workers=2,
            max_pages=None,
            page_size=500,
            resume=False,
            preflight=False,
            validate_counts=False,
            filter_fn=lambda s: f'spec.importer_data.project_uuid=="{s.key}"',
            facade_attr="DependencyMetadata",
            record_builder=lambda rows, shard: [
                {"uuid": row["uuid"], "project_uuid": shard.key} for row in rows
            ],
        )

    worker = threading.Thread(target=_collect_in_thread)
    worker.start()

    saw_partial = False
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and worker.is_alive():
        loaded = load_collect_manifest(tmp_path)
        assert loaded is not None
        complete = sum(
            1
            for shard in loaded.resources[RESOURCE_DEPENDENCY_METADATA].shards.values()
            if shard.status == "complete"
        )
        if complete >= 1:
            saw_partial = True
            break
        time.sleep(0.05)

    assert saw_partial
    assert worker.is_alive()
    release_slow.set()
    worker.join(timeout=5.0)
    assert not worker.is_alive()
