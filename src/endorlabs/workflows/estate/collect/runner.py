"""Sharded estate workspace collect with atomic manifest and resume."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from endorlabs.filters import main_context_filter
from endorlabs.tools.list_sharding import (
    ProjectShard,
    parallel_map_shards_iter,
    project_dict_to_shard,
)
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.estate.collect.bounds import (
    count_for_progress,
    count_list_delta_check,
    resolve_collect_max_workers,
    resolve_max_pages,
)
from endorlabs.workflows.estate.collect.dependency_metadata import (
    dependency_metadata_record_from_row,
)
from endorlabs.workflows.estate.collect.findings import findings_filter_for_project
from endorlabs.workflows.estate.collect.projects import (
    collect_project_resource,
    load_project_records,
)
from endorlabs.workflows.estate.contracts import (
    RESOURCE_DEPENDENCY_METADATA,
    RESOURCE_FINDING,
    RESOURCE_PACKAGE_VERSION,
    RESOURCE_PROJECT,
)
from endorlabs.workflows.estate.filters.masks import DEP_METADATA_LIST_MASK
from endorlabs.workflows.estate.workspace.collect_manifest import (
    CollectManifest,
    create_or_load_manifest,
    finalize_resource,
    init_shards,
    mark_shard_complete,
    mark_shard_failed,
    pending_shard_keys,
    reset_manifest_for_overwrite,
    save_collect_manifest,
)
from endorlabs.workflows.estate.workspace.paths import (
    ensure_workspace_layout,
    resource_path,
    workspace_dir_for,
)
from endorlabs.workflows.query_collect import collect_project_findings_via_query

if TYPE_CHECKING:
    from endorlabs import Client

LOGGER = get_resource_logger(__name__)


@dataclass(frozen=True, slots=True)
class CollectResult:
    workspace_root: Path
    resources: dict[str, str]


def _resolve_workspace(
    *,
    namespace: str,
    workspace: str | Path | None,
    date_suffix: str | None = None,
) -> Path:
    if workspace is not None:
        path = Path(workspace)
        if path.is_file():
            from endorlabs.workflows.estate.workspace.paths import (
                resolve_workspace_root,
            )

            return resolve_workspace_root(path)
        return path
    return workspace_dir_for(".endorlabs-context", namespace, date_suffix=date_suffix)


def _project_shards(
    client: Client,
    namespace: str,
    workspace_root: Path,
) -> list[ProjectShard]:
    rows = load_project_records(workspace_root)
    if rows:
        return [project_dict_to_shard(row, namespace) for row in rows]
    return client.Query.Project.discover(namespace, traverse=True).project_shards()


def _preflight_shard(
    client: Client,
    shard: ProjectShard,
    *,
    facade_attr: str,
    filter_expr: str,
) -> int | None:
    facade = getattr(client, facade_attr)
    return count_for_progress(
        facade,
        shard.namespace,
        resource_label=facade_attr,
        filter_expr=filter_expr,
        logger=LOGGER,
    )


def _collect_sharded_resource(
    client: Client,
    *,
    namespace: str,
    workspace_root: Path,
    manifest: CollectManifest,
    resource_id: str,
    max_workers: int,
    max_pages: int | None,
    page_size: int,
    resume: bool,
    preflight: bool,
    validate_counts: bool,
    filter_fn: Callable[[ProjectShard], str],
    facade_attr: str,
    record_builder: Callable[[list, ProjectShard], list[dict]],
) -> int:
    shards = _project_shards(client, namespace, workspace_root)
    shard_keys = [s.project_uuid for s in shards]
    init_shards(manifest, resource_id, shard_keys)

    pending_keys = pending_shard_keys(manifest, resource_id, resume=resume)
    pending_shards = [s for s in shards if s.project_uuid in pending_keys]

    out_path = resource_path(workspace_root, resource_id)
    if not resume or not out_path.is_file():
        safe_write_text(workspace_root, out_path, "")

    total_rows = 0
    errors: list[str] = []

    def _worker(shard: ProjectShard) -> tuple[str, list[dict], str | None, int | None]:
        filt = filter_fn(shard)
        expected: int | None = None
        if preflight:
            expected = _preflight_shard(
                client, shard, facade_attr=facade_attr, filter_expr=filt
            )
        try:
            rows = client.DependencyMetadata.list(
                filter=filt,
                namespace=shard.namespace,
                mask=DEP_METADATA_LIST_MASK,
                max_pages=max_pages,
                page_size=page_size,
            )
            records = record_builder(rows, shard)
            return shard.project_uuid, records, None, expected
        except Exception as exc:
            return shard.project_uuid, [], f"{shard.project_uuid}: {exc}", expected

    with out_path.open("a", encoding="utf-8") as handle:
        for shard_key, batch, err, expected_count in parallel_map_shards_iter(
            pending_shards,
            _worker,
            max_workers=max_workers,
            progress_label=f"{resource_id} shards",
        ):
            if err:
                errors.append(err)
                mark_shard_failed(manifest, resource_id, shard_key, err)
                save_collect_manifest(workspace_root, manifest)
                continue
            for row in batch:
                handle.write(json.dumps(row, ensure_ascii=False))
                handle.write("\n")
            total_rows += len(batch)
            mark_shard_complete(
                manifest,
                resource_id,
                shard_key,
                line_count=len(batch),
                expected_count=expected_count,
            )
            save_collect_manifest(workspace_root, manifest)

    for row in manifest.resources[resource_id].shards.values():
        if (
            validate_counts
            and row.expected_count is not None
            and row.status == "complete"
        ):
            ok, detail = count_list_delta_check(
                in_scope_count=row.expected_count,
                actual_row_count=row.line_count,
            )
            if not ok:
                LOGGER.warning("Shard validation: %s", detail)

    file_lines = sum(
        shard.line_count
        for shard in manifest.resources[resource_id].shards.values()
        if shard.status == "complete"
    )
    status = "complete" if not errors else ("partial" if file_lines else "failed")
    finalize_resource(
        manifest,
        resource_id,
        status=status,
        line_count=file_lines,
        filter_summary=main_context_filter(),
    )
    save_collect_manifest(workspace_root, manifest)
    return file_lines


def _collect_package_version(
    client: Client,
    *,
    namespace: str,
    workspace_root: Path,
    manifest: CollectManifest,
    max_pages: int | None,
    page_size: int,
    max_workers: int,
) -> int:
    from endorlabs.workflows.estate.analyze.compile_graph.pipeline import (
        build_publisher_index,
    )

    project_set = {
        str(r.get("uuid"))
        for r in load_project_records(workspace_root)
        if r.get("uuid")
    }
    if not project_set:
        for shard in client.Query.Project.discover(
            namespace, traverse=True
        ).project_shards():
            project_set.add(shard.project_uuid)

    _, _, published_by_project, _ = build_publisher_index(
        client,
        namespace=namespace,
        project_set=project_set,
        max_pages=max_pages,
        page_size=page_size,
        max_workers=max_workers,
    )
    out_path = resource_path(workspace_root, RESOURCE_PACKAGE_VERSION)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as handle:
        for project_uuid, rows in published_by_project.items():
            for row in rows:
                record = {**row, "project_uuid": project_uuid}
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
                count += 1
    finalize_resource(
        manifest,
        RESOURCE_PACKAGE_VERSION,
        status="complete",
        line_count=count,
        filter_summary=main_context_filter(),
    )
    save_collect_manifest(workspace_root, manifest)
    return count


def _collect_dm_and_finding_parallel(
    client: Client,
    *,
    namespace: str,
    workspace_root: Path,
    manifest: CollectManifest,
    max_workers: int,
    max_pages: int | None,
    page_size: int,
    resume: bool,
    preflight: bool,
    validate_counts: bool,
) -> tuple[int, int]:
    dm_count = 0
    finding_count = 0

    def _run_dm() -> int:
        return _collect_sharded_resource(
            client,
            namespace=namespace,
            workspace_root=workspace_root,
            manifest=manifest,
            resource_id=RESOURCE_DEPENDENCY_METADATA,
            max_workers=max_workers,
            max_pages=max_pages,
            page_size=page_size,
            resume=resume,
            preflight=preflight,
            validate_counts=validate_counts,
            filter_fn=lambda s: main_context_filter(
                f'spec.importer_data.project_uuid=="{s.project_uuid}"'
            ),
            facade_attr="DependencyMetadata",
            record_builder=lambda rows, shard: [
                dependency_metadata_record_from_row(r, project_uuid=shard.project_uuid)
                for r in (rows or [])
            ],
        )

    def _run_finding() -> int:
        topology = client.Query.Project.discover(namespace, traverse=True)
        projects = topology.projects
        shard_keys = [p.uuid for p in projects]
        init_shards(manifest, RESOURCE_FINDING, shard_keys)
        rows = collect_project_findings_via_query(
            client,
            projects,
            max_root_pages=max_pages,
        )
        records = [
            {**row, "project_uuid": row.get("project_uuid") or ""} for row in rows
        ]
        out_path = resource_path(workspace_root, RESOURCE_FINDING)
        if not resume or not out_path.is_file():
            safe_write_text(workspace_root, out_path, "")
        with out_path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
        finalize_resource(
            manifest,
            RESOURCE_FINDING,
            status="complete",
            line_count=len(records),
            filter_summary=findings_filter_for_project(""),
        )
        save_collect_manifest(workspace_root, manifest)
        return len(records)

    dm_count = _run_dm()
    finding_count = _run_finding()
    return dm_count, finding_count


def collect_workspace(
    client: Client,
    *,
    namespace: str,
    workspace: str | Path | None = None,
    date_suffix: str | None = None,
    max_workers: int | None = None,
    max_pages: int | None = None,
    page_size: int = 500,
    resume: bool = False,
    overwrite: bool = False,
    preflight: bool = False,
    validate_counts: bool = False,
) -> CollectResult:
    """Collect all estate resources into a workspace directory."""
    workspace_root = _resolve_workspace(
        namespace=namespace,
        workspace=workspace,
        date_suffix=date_suffix,
    )
    ensure_workspace_layout(workspace_root)
    workers = resolve_collect_max_workers(max_workers)
    LOGGER.info("Collect max_workers=%s", workers)

    if overwrite:
        manifest = reset_manifest_for_overwrite(workspace_root, namespace)
        for resource_id in (
            RESOURCE_PROJECT,
            RESOURCE_DEPENDENCY_METADATA,
            RESOURCE_FINDING,
            RESOURCE_PACKAGE_VERSION,
        ):
            path = resource_path(workspace_root, resource_id)
            if path.is_file():
                safe_write_text(workspace_root, path, "")
    else:
        manifest = create_or_load_manifest(workspace_root, namespace)

    resolved_pages = resolve_max_pages(max_pages)
    outcomes: dict[str, str] = {}

    project_rec = manifest.resources[RESOURCE_PROJECT]
    if overwrite or project_rec.status != "complete":
        rows, _ = collect_project_resource(
            client,
            namespace=namespace,
            workspace_root=workspace_root,
            max_pages=resolved_pages,
            page_size=page_size,
            max_workers=workers,
        )
        keys = [str(r["uuid"]) for r in rows if r.get("uuid")]
        finalize_resource(
            manifest,
            RESOURCE_PROJECT,
            status="complete",
            line_count=len(rows),
            keys=keys,
            filter_summary="traverse=true",
        )
        save_collect_manifest(workspace_root, manifest)
        outcomes[RESOURCE_PROJECT] = f"{len(rows)} projects"
    else:
        outcomes[RESOURCE_PROJECT] = f"{project_rec.line_count} projects (cached)"

    dm_status = manifest.resources[RESOURCE_DEPENDENCY_METADATA].status
    finding_status = manifest.resources[RESOURCE_FINDING].status
    if overwrite or dm_status != "complete" or finding_status != "complete":
        dm_count, finding_count = _collect_dm_and_finding_parallel(
            client,
            namespace=namespace,
            workspace_root=workspace_root,
            manifest=manifest,
            max_workers=workers,
            max_pages=resolved_pages,
            page_size=page_size,
            resume=resume and not overwrite,
            preflight=preflight,
            validate_counts=validate_counts,
        )
        outcomes[RESOURCE_DEPENDENCY_METADATA] = f"{dm_count} dm rows"
        outcomes[RESOURCE_FINDING] = f"{finding_count} findings"
    else:
        outcomes[RESOURCE_DEPENDENCY_METADATA] = (
            f"{manifest.resources[RESOURCE_DEPENDENCY_METADATA].line_count} dm rows (cached)"
        )
        outcomes[RESOURCE_FINDING] = (
            f"{manifest.resources[RESOURCE_FINDING].line_count} findings (cached)"
        )

    pv_rec = manifest.resources[RESOURCE_PACKAGE_VERSION]
    if overwrite or pv_rec.status != "complete":
        pv_count = _collect_package_version(
            client,
            namespace=namespace,
            workspace_root=workspace_root,
            manifest=manifest,
            max_pages=resolved_pages,
            page_size=page_size,
            max_workers=workers,
        )
        outcomes[RESOURCE_PACKAGE_VERSION] = f"{pv_count} package versions"
    else:
        outcomes[RESOURCE_PACKAGE_VERSION] = (
            f"{pv_rec.line_count} package versions (cached)"
        )

    return CollectResult(workspace_root=workspace_root, resources=outcomes)
