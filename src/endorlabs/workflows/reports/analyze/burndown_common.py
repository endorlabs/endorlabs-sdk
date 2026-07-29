"""Shared path/tag redistribute helpers for FindingLog burndown reports."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import TYPE_CHECKING, Any

from endorlabs.workflows.findings.finding_log_trends import (
    empty_series_cell,
    sum_series_cells,
)

if TYPE_CHECKING:
    from endorlabs import Client

SEV_KEYS = ("all", "critical", "high", "medium", "low")
PULL_MODE_PROJECT_GRAIN = "project_grain_redistribute"
DEFAULT_BURNDOWN_WORKERS = 24

MatrixFn = Callable[..., dict[str, dict[str, dict[str, Any]]]]


def empty_facet_matrix(
    categories: list[str],
    period_caption: str,
    facet_keys: tuple[str, ...] | list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Zero-filled severity × facet matrix."""
    return {
        sev: {
            facet: empty_series_cell(categories, period_caption) for facet in facet_keys
        }
        for sev in SEV_KEYS
    }


def sum_severity_facet_matrices(
    parts: list[dict[str, dict[str, dict[str, Any]]]],
    *,
    categories: list[str],
    period_caption: str,
    facet_keys: tuple[str, ...] | list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Sum severity×facet series matrices cell-wise."""
    if not parts:
        return empty_facet_matrix(categories, period_caption, facet_keys)
    built: dict[str, dict[str, dict[str, Any]]] = {}
    for sev in SEV_KEYS:
        built[sev] = {}
        for facet in facet_keys:
            cells = [
                matrix[sev][facet]
                for matrix in parts
                if sev in matrix and facet in matrix[sev]
            ]
            built[sev][facet] = sum_series_cells(
                cells, categories=categories, period_caption=period_caption
            )
    return built


def roll_project_matrices(
    project_matrices: dict[str, dict[str, dict[str, dict[str, Any]]]],
    uuids: list[str],
    *,
    categories: list[str],
    period_caption: str,
    facet_keys: tuple[str, ...] | list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Sum project matrices for the given UUID set."""
    parts = [project_matrices[uid] for uid in uuids if uid in project_matrices]
    return sum_severity_facet_matrices(
        parts,
        categories=categories,
        period_caption=period_caption,
        facet_keys=facet_keys,
    )


def pull_project_matrices(
    client: Client,
    projects: list[dict[str, Any]],
    *,
    matrix_fn: MatrixFn,
    matrix_kwargs: dict[str, Any],
    facet_keys: tuple[str, ...] | list[str],
    categories: list[str],
    period_caption: str,
    max_workers: int,
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Pull one FindingLog severity×facet matrix per project (parallel)."""

    def _one(
        project: dict[str, Any],
    ) -> tuple[str, dict[str, dict[str, dict[str, Any]]]]:
        uid = str(project["uuid"])
        ns = str(project.get("namespace") or "")
        try:
            matrix = matrix_fn(
                client,
                namespace=ns,
                parent_uuids=[uid],
                categories=categories,
                period_caption=period_caption,
                **matrix_kwargs,
            )
        except Exception:
            matrix = empty_facet_matrix(categories, period_caption, facet_keys)
        return uid, matrix

    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    if not projects:
        return out
    workers = max(1, max_workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, project) for project in projects]
        for fut in as_completed(futures):
            uid, matrix = fut.result()
            out[uid] = matrix
    return out


def build_path_and_tag_series(
    client: Client,
    *,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
    path_options: list[str],
    tag_catalog: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
    lookback: int,
    categories: list[str],
    period_caption: str,
    facet_keys: tuple[str, ...] | list[str],
    matrix_fn: MatrixFn,
    matrix_kwargs: dict[str, Any],
    min_projects: int,
    max_workers: int,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Leaf path series + tagged-project redistribute for one facet matrix shape.

    Returns ``(series_filters, tag_series, tag_series_meta)``.
    """
    leaf_cells: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for ns in leaf_namespaces:
        try:
            leaf_cells[ns] = matrix_fn(
                client,
                namespace=ns,
                window_start=window_start,
                window_end=window_end,
                parent_uuids=None,
                lookback=lookback,
                categories=categories,
                period_caption=period_caption,
                **matrix_kwargs,
            )
        except Exception:
            leaf_cells[ns] = empty_facet_matrix(categories, period_caption, facet_keys)

    def roll_path(path: str) -> dict[str, dict[str, dict[str, Any]]]:
        if path == "all":
            keys = list(leaf_cells)
        else:
            keys = [ns for ns in leaf_cells if ns == path or ns.startswith(path + ".")]
        return sum_severity_facet_matrices(
            [leaf_cells[ns] for ns in keys],
            categories=categories,
            period_caption=period_caption,
            facet_keys=facet_keys,
        )

    series_filters = {"perPath": {path: roll_path(path) for path in path_options}}

    by_uuid = {p["uuid"]: p for p in projects}
    tagged_projects = [
        p for p in projects if p.get("tags") and p.get("namespace") and p.get("uuid")
    ]
    pull_kwargs = {
        "window_start": window_start,
        "window_end": window_end,
        "lookback": lookback,
        **matrix_kwargs,
    }
    project_matrices = pull_project_matrices(
        client,
        tagged_projects,
        matrix_fn=matrix_fn,
        matrix_kwargs=pull_kwargs,
        facet_keys=facet_keys,
        categories=categories,
        period_caption=period_caption,
        max_workers=max_workers,
    )

    per_tag: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}
    ready: list[str] = []
    pending: list[str] = []
    for entry in tag_catalog:
        tag = entry["tag"]
        uuids = [u for u in entry.get("projectUuids") or [] if u in by_uuid]
        if len(uuids) < min_projects:
            pending.append(tag)
            continue
        pulled = [u for u in uuids if u in project_matrices]
        if not pulled:
            pending.append(tag)
            continue
        tagged_rows = [by_uuid[u] for u in pulled]
        tag_leaf: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for ns in leaf_namespaces:
            ns_uuids = [p["uuid"] for p in tagged_rows if p.get("namespace") == ns]
            if not ns_uuids:
                continue
            tag_leaf[ns] = roll_project_matrices(
                project_matrices,
                ns_uuids,
                categories=categories,
                period_caption=period_caption,
                facet_keys=facet_keys,
            )
        path_map: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for path in path_options:
            if path == "all":
                keys = list(tag_leaf)
            else:
                keys = [
                    ns for ns in tag_leaf if ns == path or ns.startswith(path + ".")
                ]
            if not keys:
                continue
            path_map[path] = sum_severity_facet_matrices(
                [tag_leaf[ns] for ns in keys],
                categories=categories,
                period_caption=period_caption,
                facet_keys=facet_keys,
            )
        if path_map:
            per_tag[tag] = path_map
            ready.append(tag)
        else:
            pending.append(tag)

    tag_series = {"tags": ready, "perTag": per_tag}
    tag_series_meta = {
        "seriesReady": ready,
        "seriesPending": pending,
        "seriesReadyCount": len(ready),
        "seriesPendingCount": len(pending),
        "pullPolicy": {
            "minProjects": min_projects,
            "mode": PULL_MODE_PROJECT_GRAIN,
            "taggedProjectsPulled": len(project_matrices),
            "workers": max(1, max_workers),
        },
    }
    return series_filters, tag_series, tag_series_meta


def build_category_burndown_block(
    client: Client,
    *,
    tenant: str,
    projects: list[dict[str, Any]],
    leaf_namespaces: list[str],
    path_options: list[str],
    tag_catalog: list[dict[str, Any]],
    category_key: str,
    lookback: int,
    min_projects: int,
    max_workers: int,
    categories: list[str] | None = None,
    period_caption: str | None = None,
) -> dict[str, Any]:
    """Build one FindingLog burndown block from a shared category spec."""
    from endorlabs.workflows.findings.finding_log_trends import (
        compute_window,
        query_severity_facet_matrix,
        query_severity_facet_series_cell,
    )
    from endorlabs.workflows.reports.analyze.finding_burndown_specs import (
        get_category_spec,
    )

    spec = get_category_spec(category_key)
    base_filter = spec["base_filter"]()
    facet_keys = tuple(spec["facet_keys"])
    cells = spec["cells"]
    expand = str(spec.get("expand") or "severity")
    seed_clause = str(spec.get("seed_facet_clause") or "")
    window_start, window_end = compute_window(lookback=lookback)

    if not categories or not period_caption:
        seed = query_severity_facet_series_cell(
            client,
            namespace=tenant,
            window_start=window_start,
            window_end=window_end,
            category_base_filter=base_filter,
            facet_clause=seed_clause,
            level="CRITICAL",
            parent_uuids=None,
            lookback=lookback,
        )
        categories = list(seed["categories"])
        period_caption = str(seed["periodCaption"])

    def matrix_fn(
        client_: Client, **kwargs: Any
    ) -> dict[str, dict[str, dict[str, Any]]]:
        return query_severity_facet_matrix(
            client_,
            category_base_filter=base_filter,
            cells=cells,
            facet_keys=facet_keys,
            expand=expand,
            **kwargs,
        )

    series_filters, tag_series, tag_series_meta = build_path_and_tag_series(
        client,
        projects=projects,
        leaf_namespaces=leaf_namespaces,
        path_options=path_options,
        tag_catalog=tag_catalog,
        window_start=window_start,
        window_end=window_end,
        lookback=lookback,
        categories=categories,
        period_caption=period_caption,
        facet_keys=facet_keys,
        matrix_fn=matrix_fn,
        matrix_kwargs={},
        min_projects=min_projects,
        max_workers=max_workers,
    )
    return {
        "findingCriteria": spec["criteria"],
        "lookback": lookback,
        "interval": "week",
        "facetKeys": list(facet_keys),
        "expand": expand,
        "seriesFilters": series_filters,
        "tagSeries": tag_series,
        "tagSeriesMeta": tag_series_meta,
        "periodCaption": period_caption,
    }
