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
PULL_MODE_TAG_IS_IN = "tag_parent_uuid_is_in"
DEFAULT_BURNDOWN_WORKERS = 24

# CI / PR ScanResult + FindingLog retention is typically ~30d.
PR_LOOKBACK_DAYS = 30
PR_LOOKBACK_WEEKS = max(1, PR_LOOKBACK_DAYS // 7)

SCOPE_MAIN = "main"
SCOPE_PR = "pr"

SERIES_LABELS_MAIN = {
    "primary": "New",
    "secondary": "Resolved",
    "cumulativePrimary": "Cumulative new",
    "cumulativeSecondary": "Cumulative resolved",
    "windowNet": "Window net",
    "weeklyCard": "Weekly new vs resolved",
    "cumulativeCard": "Cumulative new vs resolved · window net",
}
SERIES_LABELS_PR = {
    "primary": "Detected",
    "secondary": "Blocked",
    "cumulativePrimary": "Cumulative detected",
    "cumulativeSecondary": "Cumulative blocked",
    "windowNet": "Detected − blocked",
    "weeklyCard": "Weekly detected vs blocked (PR)",
    "cumulativeCard": "Cumulative detected vs blocked · PR window",
}

MatrixFn = Callable[..., dict[str, dict[str, dict[str, Any]]]]


def pr_active_project_uuids(cadence: dict[str, Any] | None) -> list[str]:
    """UUIDs with ≥1 CI/PR ScanResult in the cadence window (evidence-based)."""
    by_project = (cadence or {}).get("byProject") or {}
    out: list[str] = []
    for uid, cell in by_project.items():
        if int((cell or {}).get("ciScans") or 0) > 0:
            out.append(str(uid))
    return sorted(out)


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


def _uuids_for_path(
    projects_by_uuid: dict[str, dict[str, Any]],
    uuids: list[str],
    path: str,
) -> list[str]:
    """Filter project UUIDs to those whose namespace matches *path* (or all)."""
    if path == "all":
        return list(uuids)
    out: list[str] = []
    for uid in uuids:
        row = projects_by_uuid.get(uid) or {}
        ns = str(row.get("namespace") or "")
        if ns == path or ns.startswith(path + "."):
            out.append(uid)
    return out


def pull_is_in_matrices(
    client: Client,
    *,
    tenant: str,
    jobs: list[tuple[str, list[str]]],
    matrix_fn: MatrixFn,
    matrix_kwargs: dict[str, Any],
    facet_keys: tuple[str, ...] | list[str],
    categories: list[str],
    period_caption: str,
    max_workers: int,
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Pull FindingLog severity×facet matrices via ``parent_uuid is_in`` (parallel).

    *jobs* are ``(job_key, parent_uuids)``. Each call uses *tenant* +
    ``traverse=True`` (via the resilient FindingLog helper) so child-namespace
    projects are included.
    """

    def _one(
        item: tuple[str, list[str]],
    ) -> tuple[str, dict[str, dict[str, dict[str, Any]]]]:
        key, uuids = item
        try:
            matrix = matrix_fn(
                client,
                namespace=tenant,
                parent_uuids=uuids,
                categories=categories,
                period_caption=period_caption,
                **matrix_kwargs,
            )
        except Exception:
            matrix = empty_facet_matrix(categories, period_caption, facet_keys)
        return key, matrix

    out: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    if not jobs:
        return out
    workers = max(1, min(max_workers, len(jobs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, job) for job in jobs]
        for fut in as_completed(futures):
            key, matrix = fut.result()
            out[key] = matrix
    return out


def build_path_and_tag_series(
    client: Client,
    *,
    tenant: str,
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
    project_uuid_allowlist: list[str] | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    """Leaf path series + tag-grain ``parent_uuid is_in`` for one facet matrix.

    MAIN path series use leaf-namespace aggregates (includes untagged projects).
    When *project_uuid_allowlist* is set (PR-active), path series use one
    ``is_in`` pull per path over that UUID set.

    Tag series: one ``is_in`` pull per (tag, path) at *tenant* with
    ``traverse=True`` (via resilient FindingLog helpers).

    Returns ``(series_filters, tag_series, tag_series_meta)``.
    """
    allow = set(project_uuid_allowlist) if project_uuid_allowlist is not None else None
    scoped_projects = (
        [p for p in projects if str(p.get("uuid") or "") in allow]
        if allow is not None
        else projects
    )
    by_uuid = {p["uuid"]: p for p in scoped_projects if p.get("uuid")}

    pull_kwargs = {
        "window_start": window_start,
        "window_end": window_end,
        "lookback": lookback,
        **matrix_kwargs,
    }

    leaf_cells: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}

    def _leaf_one(ns: str) -> tuple[str, dict[str, dict[str, dict[str, Any]]]]:
        try:
            matrix = matrix_fn(
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
            matrix = empty_facet_matrix(categories, period_caption, facet_keys)
        return ns, matrix

    series_filters: dict[str, Any]
    if allow is None:
        if leaf_namespaces:
            workers = max(1, min(max_workers, len(leaf_namespaces)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_leaf_one, ns) for ns in leaf_namespaces]
                for fut in as_completed(futures):
                    ns, matrix = fut.result()
                    leaf_cells[ns] = matrix

        def roll_path(path: str) -> dict[str, dict[str, dict[str, Any]]]:
            if path == "all":
                keys = list(leaf_cells)
            else:
                keys = [
                    ns for ns in leaf_cells if ns == path or ns.startswith(path + ".")
                ]
            return sum_severity_facet_matrices(
                [leaf_cells[ns] for ns in keys],
                categories=categories,
                period_caption=period_caption,
                facet_keys=facet_keys,
            )

        series_filters = {"perPath": {path: roll_path(path) for path in path_options}}
    else:
        path_jobs: list[tuple[str, list[str]]] = []
        allow_uuids = [str(p["uuid"]) for p in scoped_projects if p.get("uuid")]
        for path in path_options:
            path_uuids = _uuids_for_path(by_uuid, allow_uuids, path)
            if path_uuids:
                path_jobs.append((f"path:{path}", path_uuids))
        path_matrices = pull_is_in_matrices(
            client,
            tenant=tenant,
            jobs=path_jobs,
            matrix_fn=matrix_fn,
            matrix_kwargs=pull_kwargs,
            facet_keys=facet_keys,
            categories=categories,
            period_caption=period_caption,
            max_workers=max_workers,
        )
        path_map: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for path in path_options:
            key = f"path:{path}"
            if key in path_matrices:
                path_map[path] = path_matrices[key]
        series_filters = {"perPath": path_map}

    tag_jobs: list[tuple[str, list[str]]] = []
    ready_candidates: list[tuple[str, list[str]]] = []
    pending: list[str] = []
    for entry in tag_catalog:
        tag = str(entry["tag"])
        uuids = [
            u
            for u in entry.get("projectUuids") or []
            if u in by_uuid and (allow is None or u in allow)
        ]
        if len(uuids) < min_projects:
            pending.append(tag)
            continue
        ready_candidates.append((tag, uuids))
        for path in path_options:
            path_uuids = _uuids_for_path(by_uuid, uuids, path)
            if path_uuids:
                tag_jobs.append((f"tag:{tag}|{path}", path_uuids))

    tag_matrices = pull_is_in_matrices(
        client,
        tenant=tenant,
        jobs=tag_jobs,
        matrix_fn=matrix_fn,
        matrix_kwargs=pull_kwargs,
        facet_keys=facet_keys,
        categories=categories,
        period_caption=period_caption,
        max_workers=max_workers,
    )

    per_tag: dict[str, dict[str, dict[str, dict[str, dict[str, Any]]]]] = {}
    ready: list[str] = []
    for tag, _uuids in ready_candidates:
        tag_path_map: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
        for path in path_options:
            key = f"tag:{tag}|{path}"
            if key in tag_matrices:
                tag_path_map[path] = tag_matrices[key]
        if tag_path_map:
            per_tag[tag] = tag_path_map
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
            "mode": PULL_MODE_TAG_IS_IN,
            "isInPulls": len(tag_jobs),
            "workers": max(1, max_workers),
            "projectAllowlist": len(allow) if allow is not None else None,
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
    context_scope: str = SCOPE_MAIN,
    project_uuid_allowlist: list[str] | None = None,
) -> dict[str, Any]:
    """Build one FindingLog burndown block from a shared category spec.

    *context_scope* ``main`` uses MAIN CREATE/DELETE; ``pr`` uses CI_RUN CREATE
    vs CREATE∩CI_BLOCKER (Detected/Blocked) with a shorter lookback when the
    caller passes :data:`PR_LOOKBACK_WEEKS`.
    """
    from endorlabs.filters import to_ci_context_filter
    from endorlabs.workflows.findings.finding_log_trends import (
        compute_window,
        query_severity_facet_matrix,
        query_severity_facet_series_cell,
    )
    from endorlabs.workflows.reports.analyze.finding_burndown_specs import (
        get_category_spec,
    )

    if context_scope not in {SCOPE_MAIN, SCOPE_PR}:
        msg = f"unsupported context_scope={context_scope!r}"
        raise ValueError(msg)

    spec = get_category_spec(category_key)
    base_filter = spec["base_filter"]()
    second_series = "delete"
    series_labels = SERIES_LABELS_MAIN
    if context_scope == SCOPE_PR:
        base_filter = to_ci_context_filter(base_filter)
        second_series = "ci_blocker"
        series_labels = SERIES_LABELS_PR
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
            max_workers=max_workers,
            second_series=second_series,
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
            max_workers=max_workers,
            second_series=second_series,
            **kwargs,
        )

    series_filters, tag_series, tag_series_meta = build_path_and_tag_series(
        client,
        tenant=tenant,
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
        project_uuid_allowlist=project_uuid_allowlist,
    )
    criteria = str(spec["criteria"])
    if context_scope == SCOPE_PR:
        criteria = (
            criteria.replace("main context", "PR / CI_RUN context")
            + " · Detected=CREATE · Blocked=CREATE∩CI_BLOCKER"
        )
    return {
        "findingCriteria": criteria,
        "lookback": lookback,
        "lookbackDays": lookback * 7 if context_scope == SCOPE_PR else None,
        "interval": "week",
        "contextScope": context_scope,
        "seriesLabels": dict(series_labels),
        "facetKeys": list(facet_keys),
        "expand": expand,
        "seriesFilters": series_filters,
        "tagSeries": tag_series,
        "tagSeriesMeta": tag_series_meta,
        "periodCaption": period_caption,
    }


def attach_main_pr_scopes(
    main_block: dict[str, Any],
    pr_block: dict[str, Any] | None,
    *,
    pr_active_uuids: list[str] | None = None,
) -> dict[str, Any]:
    """Nest MAIN + PR blocks under ``scopes``; keep MAIN fields at the root."""
    out = dict(main_block)
    scopes: dict[str, Any] = {SCOPE_MAIN: main_block}
    if pr_block is not None:
        scopes[SCOPE_PR] = pr_block
    out["scopes"] = scopes
    if pr_active_uuids is not None:
        out["prActiveProjectUuids"] = list(pr_active_uuids)
    return out
