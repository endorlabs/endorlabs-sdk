"""Phase 1 — MAIN-context DependencyMetadata inventory (sharded, resumable)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.filters import main_context_filter
from endorlabs.tools.list_bounds import (
    resolve_collect_max_workers,
    resolve_max_pages,
)
from endorlabs.tools.list_sharding import (
    ProjectShard,
    parallel_map_shards_iter,
    project_model_to_shard,
)
from endorlabs.utils.jsonl_store import JsonlKeyedStore, load_jsonl_rows
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.license_export.checkpoint import (
    NamespaceCheckpoint,
    init_shards,
    load_checkpoint,
    mark_complete,
    mark_failed,
    pending_shard_keys,
    save_checkpoint,
)
from endorlabs.workflows.license_export.masks import DM_LICENSE_EXPORT_MASK
from endorlabs.workflows.wire_access import nested_dict

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

LOGGER = get_resource_logger(__name__)

INVENTORY_FILENAME = "dependency_inventory.jsonl"
PROJECTS_FILENAME = "projects.jsonl"
INVENTORY_KEY_FIELDS: tuple[str, ...] = ("project_uuid", "package_version_uuid")
PROJECTS_KEY_FIELDS: tuple[str, ...] = ("uuid",)


@dataclass
class InventoryResult(WorkflowResult):
    """Outcome of a MAIN-context DM inventory for one namespace."""

    namespace: str = ""
    output_dir: str = ""
    inventory_path: str = ""
    projects_path: str = ""
    project_count: int = 0
    row_count: int = 0
    failed_shards: int = 0
    complete_shards: int = 0


def inventory_paths(output_dir: Path) -> tuple[Path, Path]:
    """Return ``(dependency_inventory.jsonl, projects.jsonl)`` under *output_dir*."""
    return output_dir / INVENTORY_FILENAME, output_dir / PROJECTS_FILENAME


def compose_dm_list_filter(project_uuid: str, extra_filter: str | None = None) -> str:
    """MAIN + importer UUID, optionally AND-ed with caller *extra_filter*.

    Callers cannot drop the mandatory MAIN / importer safety clauses.
    """
    base = main_context_filter(f'spec.importer_data.project_uuid=="{project_uuid}"')
    extra = (extra_filter or "").strip()
    if not extra:
        return base
    return f"({base}) and ({extra})"


def project_name_from_project(project: Any) -> str:
    """Return ``Project.meta.name`` (or DiscoveredProject.name); empty if absent.

    Does not invent names from other fields. Topology's uuid-fill for missing
    ``meta.name`` is treated as empty for export rows.
    """
    meta = getattr(project, "meta", None)
    if meta is not None:
        name = getattr(meta, "name", None)
        return str(name).strip() if name else ""
    name = getattr(project, "name", None)
    text = str(name).strip() if name is not None else ""
    uuid = str(getattr(project, "uuid", "") or "")
    if text and text == uuid:
        return ""
    return text


def _row_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    dump = getattr(row, "model_dump", None)
    if callable(dump):
        data = dump(mode="json", exclude_none=False)
        if isinstance(data, dict):
            return dict(data)
    raise TypeError(f"Unsupported DependencyMetadata row type: {type(row)!r}")


def flatten_dm_row(
    row: Any,
    *,
    namespace: str,
    project_uuid: str,
    project_name: str,
) -> dict[str, Any] | None:
    """Flatten a masked DM row to inventory grain; skip when PV UUID missing."""
    payload = _row_to_dict(row)
    dep = nested_dict(payload, "spec", "dependency_data")
    pv_uuid = str(dep.get("package_version_uuid") or "").strip()
    if not pv_uuid:
        return None
    last_commit = dep.get("last_commit")
    return {
        "namespace": namespace,
        "project_uuid": project_uuid,
        "project_name": project_name,
        "package_name": str(dep.get("package_name") or ""),
        "package_version_uuid": pv_uuid,
        "purl": str(dep.get("purl") or ""),
        "ecosystem": str(dep.get("ecosystem") or ""),
        "direct": bool(dep.get("direct")),
        "reachable": str(dep.get("reachable") or ""),
        "scope": str(dep.get("scope") or ""),
        "public": bool(dep.get("public")) if dep.get("public") is not None else False,
        "pinned": bool(dep.get("pinned")) if dep.get("pinned") is not None else False,
        "internal": (
            bool(dep.get("internal")) if dep.get("internal") is not None else False
        ),
        "vendored": (
            bool(dep.get("vendored")) if dep.get("vendored") is not None else False
        ),
        "last_commit": str(last_commit) if last_commit is not None else "",
        "resolved_version": str(dep.get("resolved_version") or ""),
        "dm_uuid": str(payload.get("uuid") or ""),
    }


def dedupe_inventory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one row per (project_uuid, package_version_uuid)."""
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = (
            str(row.get("project_uuid") or ""),
            str(row.get("package_version_uuid") or ""),
        )
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _discover_shards(client: Client, namespace: str) -> list[ProjectShard]:
    topology = client.Query.Project.discover(namespace, traverse=True)
    shards: list[ProjectShard] = []
    for project in topology.projects:
        shard = project_model_to_shard(project, namespace)
        if not shard.project_uuid:
            continue
        # Prefer explicit Project.meta.name / DiscoveredProject.name; never invent.
        name = project_name_from_project(project)
        if name != (shard.label or ""):
            shard = ProjectShard(
                project_uuid=shard.project_uuid,
                namespace=shard.namespace,
                label=name or None,
            )
        shards.append(shard)
    return shards


def _write_projects_jsonl(path: Path, shards: list[ProjectShard]) -> None:
    store = JsonlKeyedStore(path, PROJECTS_KEY_FIELDS)
    store.clear()
    for shard in shards:
        store.upsert(
            {
                "uuid": shard.project_uuid,
                "namespace": shard.namespace,
                "name": shard.label or "",
            }
        )
    store.flush()


def _run_inventory_shards(
    client: Client,
    *,
    namespace: str,
    out: Path,
    inventory_store: JsonlKeyedStore,
    checkpoint: NamespaceCheckpoint,
    pending_shards: list[ProjectShard],
    workers: int,
    pages: int | None,
    page_size: int,
    extra_filter: str | None,
    mask: str,
) -> tuple[int, list[str]]:
    errors: list[str] = []
    total_rows = 0

    def _worker(
        shard: ProjectShard,
    ) -> tuple[str, list[dict[str, Any]], str | None]:
        filt = compose_dm_list_filter(shard.project_uuid, extra_filter)
        try:
            # Projects hosted at a tenant root (no '.' in path) trip
            # NamespaceScopingError on project-scoped kinds. traverse=True
            # bypasses that guard; the importer UUID filter keeps the shard
            # scoped to one project.
            at_tenant_root = "." not in shard.namespace
            rows = client.DependencyMetadata.list(
                filter=filt,
                namespace=shard.namespace,
                mask=mask,
                max_pages=pages,
                page_size=page_size,
                traverse=at_tenant_root,
            )
            flat: list[dict[str, Any]] = []
            for row in rows or []:
                item = flatten_dm_row(
                    row,
                    namespace=namespace,
                    project_uuid=shard.project_uuid,
                    project_name=shard.label or "",
                )
                if item is not None:
                    flat.append(item)
            return shard.project_uuid, dedupe_inventory_rows(flat), None
        except Exception as exc:
            return shard.project_uuid, [], f"{shard.project_uuid}: {exc}"

    for shard_key, batch, err in parallel_map_shards_iter(
        pending_shards,
        _worker,
        max_workers=workers,
        progress_label="license-export DM shards",
    ):
        if err:
            errors.append(err)
            mark_failed(checkpoint, shard_key, err)
            save_checkpoint(out, checkpoint)
            LOGGER.warning("DM shard failed: %s", err)
            continue
        inventory_store.upsert_many(batch)
        inventory_store.flush()
        total_rows += len(batch)
        mark_complete(checkpoint, shard_key, line_count=len(batch))
        save_checkpoint(out, checkpoint)
    return total_rows, errors


def collect_dependency_inventory(
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
) -> InventoryResult:
    """Collect MAIN-context DM rows, deduped per (project, package_version).

    Uses per-project parallel lists with ``context.type==CONTEXT_TYPE_MAIN`` and
    ``spec.importer_data.project_uuid`` — the same filter shape as estate collect.
    Optional *extra_filter* is AND-ed; *mask* replaces the default DM field mask.
    Shard failures are recorded; ``resume`` retries incomplete shards only.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    inventory_path, projects_path = inventory_paths(out)
    workers = resolve_collect_max_workers(max_workers)
    pages = resolve_max_pages(max_pages if max_pages is not None else 0)
    dm_mask = (mask or "").strip() or DM_LICENSE_EXPORT_MASK

    if overwrite and inventory_path.is_file():
        inventory_path.unlink()
    if overwrite:
        resume = False

    shards = _discover_shards(client, namespace)
    _write_projects_jsonl(projects_path, shards)
    if not shards:
        return InventoryResult(
            status="success",
            message=f"No projects under {namespace!r}",
            namespace=namespace,
            output_dir=str(out),
            inventory_path=str(inventory_path),
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

    if not resume or not inventory_path.is_file():
        inventory_path.write_text("", encoding="utf-8")

    inventory_store = JsonlKeyedStore(inventory_path, INVENTORY_KEY_FIELDS)
    _total, errors = _run_inventory_shards(
        client,
        namespace=namespace,
        out=out,
        inventory_store=inventory_store,
        checkpoint=checkpoint,
        pending_shards=pending_shards,
        workers=workers,
        pages=pages,
        page_size=page_size,
        extra_filter=extra_filter,
        mask=dm_mask,
    )
    del _total
    # Final flush ensures disk matches in-memory upsert index.
    inventory_store.flush()
    total_rows = len(inventory_store)

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

    return InventoryResult(
        status=status,
        message=(
            f"Inventory {namespace}: {total_rows} rows from "
            f"{len(shards)} project(s); {failed} shard failure(s)"
        ),
        errors=errors,
        namespace=namespace,
        output_dir=str(out),
        inventory_path=str(inventory_path),
        projects_path=str(projects_path),
        project_count=len(shards),
        row_count=total_rows,
        failed_shards=failed,
        complete_shards=complete,
    )


def load_inventory_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load inventory JSONL rows from *path* (skips bad lines)."""
    return load_jsonl_rows(path)


def unique_package_version_uuids(rows: list[dict[str, Any]]) -> list[str]:
    """Ordered unique ``package_version_uuid`` values from inventory rows."""
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        pv = str(row.get("package_version_uuid") or "").strip()
        if pv and pv not in seen:
            seen.add(pv)
            out.append(pv)
    return out
