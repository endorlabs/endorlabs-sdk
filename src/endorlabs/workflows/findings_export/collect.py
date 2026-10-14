"""MAIN-context Finding inventory (sharded, resumable)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from endorlabs.filters import main_context_filter
from endorlabs.tools.list_bounds import (
    resolve_collect_max_workers,
    resolve_max_pages,
)
from endorlabs.tools.list_sharding import (
    ProjectShard,
    parallel_map_shards_iter,
    project_dict_to_shard,
    project_model_to_shard,
)
from endorlabs.utils.jsonl_store import JsonlKeyedStore
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.findings_export.checkpoint import (
    NamespaceCheckpoint,
    init_shards,
    load_checkpoint,
    mark_complete,
    mark_failed,
    pending_shard_keys,
    save_checkpoint,
)

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

LOGGER = get_resource_logger(__name__)

# Operational project discovery only — not a customer deliverable schema.
PROJECT_DISCOVERY_MASK = "uuid,meta.name,meta.tags,tenant_meta.namespace"

FINDINGS_FILENAME = "findings.jsonl"
PROJECTS_FILENAME = "projects.jsonl"
FINDINGS_KEY_FIELDS: tuple[str, ...] = ("uuid",)
PROJECTS_KEY_FIELDS: tuple[str, ...] = ("uuid",)


@dataclass
class CollectResult(WorkflowResult):
    """Outcome of a MAIN-context Finding collect for one namespace."""

    namespace: str = ""
    output_dir: str = ""
    findings_path: str = ""
    projects_path: str = ""
    project_count: int = 0
    row_count: int = 0
    failed_shards: int = 0
    complete_shards: int = 0


def compose_finding_filter(project_uuid: str, extra_filter: str | None = None) -> str:
    """MAIN + project UUID, optionally AND-ed with caller *extra_filter*.

    Callers cannot drop the mandatory MAIN / project_uuid safety clauses.
    """
    base = main_context_filter(f'spec.project_uuid=="{project_uuid}"')
    extra = (extra_filter or "").strip()
    if not extra:
        return base
    return f"({base}) and ({extra})"


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    dump = getattr(row, "model_dump", None)
    if callable(dump):
        data = dump(mode="json", exclude_none=False)
        if isinstance(data, dict):
            return cast("dict[str, Any]", data)
    return {"uuid": str(getattr(row, "uuid", "") or "")}


def _project_record(shard: ProjectShard) -> dict[str, Any]:
    return {
        "uuid": shard.project_uuid,
        "namespace": shard.namespace,
        "meta": {"name": shard.label or ""},
        "tenant_meta": {"namespace": shard.namespace},
    }


def discover_shards(client: Client, namespace: str) -> list[ProjectShard]:
    """List projects under *namespace* (traverse only at tenant root)."""
    at_root = "." not in namespace
    projects = client.Project.list(
        namespace=namespace,
        mask=PROJECT_DISCOVERY_MASK,
        traverse=at_root,
    )
    shards: list[ProjectShard] = []
    for project in projects or []:
        if isinstance(project, dict):
            shard = project_dict_to_shard(project, namespace)
        else:
            shard = project_model_to_shard(project, namespace)
        if shard.project_uuid:
            shards.append(shard)
    return shards


def _run_finding_shards(
    client: Client,
    *,
    out: Path,
    finding_store: JsonlKeyedStore,
    checkpoint: NamespaceCheckpoint,
    pending_shards: list[ProjectShard],
    workers: int,
    pages: int | None,
    page_size: int,
    extra_filter: str | None,
    mask: str | None,
) -> list[str]:
    errors: list[str] = []
    list_mask = (mask or "").strip() or None

    def _worker(
        shard: ProjectShard,
    ) -> tuple[str, list[dict[str, Any]], str | None]:
        filt = compose_finding_filter(shard.project_uuid, extra_filter)
        try:
            at_tenant_root = "." not in shard.namespace
            kwargs: dict[str, Any] = {
                "filter": filt,
                "namespace": shard.namespace,
                "max_pages": pages,
                "page_size": page_size,
                "traverse": at_tenant_root,
            }
            if list_mask is not None:
                kwargs["mask"] = list_mask
            rows = client.Finding.list(**kwargs)
            flat: list[dict[str, Any]] = []
            for row in rows or []:
                item = _row_to_dict(row)
                uuid = str(item.get("uuid") or "").strip()
                if not uuid:
                    continue
                spec = item.get("spec")
                if not isinstance(spec, dict):
                    spec = {}
                    item["spec"] = spec
                if not spec.get("project_uuid"):
                    spec["project_uuid"] = shard.project_uuid
                flat.append(item)
            return shard.project_uuid, flat, None
        except Exception as exc:
            return shard.project_uuid, [], f"{shard.project_uuid}: {exc}"

    for shard_key, batch, err in parallel_map_shards_iter(
        pending_shards,
        _worker,
        max_workers=workers,
        progress_label="findings-export shards",
    ):
        if err:
            errors.append(err)
            mark_failed(checkpoint, shard_key, err)
            save_checkpoint(out, checkpoint)
            LOGGER.warning("Finding shard failed: %s", err)
            continue
        finding_store.upsert_many(batch)
        finding_store.flush()
        mark_complete(checkpoint, shard_key, line_count=len(batch))
        save_checkpoint(out, checkpoint)
    return errors


def collect_findings_export(
    client: Client,
    *,
    namespace: str,
    output_dir: str | Path,
    max_workers: int | None = None,
    max_pages: int | None = None,
    page_size: int = 500,
    resume: bool = False,
    overwrite: bool = False,
    extra_filter: str | None = None,
    mask: str | None = None,
) -> CollectResult:
    """Collect MAIN-context Finding rows per project (no category filter).

    Uses per-project parallel ``Finding.list`` with mandatory MAIN +
    ``spec.project_uuid``. Optional *extra_filter* is AND-ed; *mask* None means
    full Finding bodies. Shard failures are recorded; ``resume`` retries
    incomplete shards only.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    findings_path = out / FINDINGS_FILENAME
    projects_path = out / PROJECTS_FILENAME
    workers = resolve_collect_max_workers(max_workers)
    pages = resolve_max_pages(max_pages if max_pages is not None else 0)

    if overwrite and findings_path.is_file():
        findings_path.unlink()
    if overwrite:
        resume = False

    shards = discover_shards(client, namespace)
    project_store = JsonlKeyedStore(projects_path, PROJECTS_KEY_FIELDS)
    project_store.clear()
    project_store.upsert_many([_project_record(s) for s in shards])
    project_store.flush()

    if not shards:
        return CollectResult(
            status="success",
            message=f"No projects under {namespace!r}",
            namespace=namespace,
            output_dir=str(out),
            findings_path=str(findings_path),
            projects_path=str(projects_path),
            project_count=0,
            row_count=0,
        )

    checkpoint = load_checkpoint(out, namespace=namespace)
    if overwrite:
        checkpoint.shards.clear()
    init_shards(checkpoint, [s.project_uuid for s in shards])
    pending = pending_shard_keys(checkpoint, resume=resume)
    pending_shards = [s for s in shards if s.project_uuid in pending]

    if not resume or not findings_path.is_file():
        findings_path.write_text("", encoding="utf-8")

    finding_store = JsonlKeyedStore(findings_path, FINDINGS_KEY_FIELDS)
    errors = _run_finding_shards(
        client,
        out=out,
        finding_store=finding_store,
        checkpoint=checkpoint,
        pending_shards=pending_shards,
        workers=workers,
        pages=pages,
        page_size=page_size,
        extra_filter=extra_filter,
        mask=mask,
    )
    finding_store.flush()
    total_rows = len(finding_store)

    failed = sum(1 for state in checkpoint.shards.values() if state.status == "failed")
    complete = sum(
        1 for state in checkpoint.shards.values() if state.status == "complete"
    )
    if errors and total_rows == 0:
        status = "error"
    elif errors:
        status = "partial"
    else:
        status = "success"

    return CollectResult(
        status=status,
        message=(
            f"Findings {namespace}: {total_rows} rows from "
            f"{len(shards)} project(s); {failed} shard failure(s)"
        ),
        errors=errors,
        namespace=namespace,
        output_dir=str(out),
        findings_path=str(findings_path),
        projects_path=str(projects_path),
        project_count=len(shards),
        row_count=total_rows,
        failed_shards=failed,
        complete_shards=complete,
    )
