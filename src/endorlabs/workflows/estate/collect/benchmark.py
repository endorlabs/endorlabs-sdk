#!/usr/bin/env python3
"""Benchmark DependencyMetadata collect strategies (S0/S1/S2) for one namespace.

Writes results under ``.endorlabs-context/workspace/runs/collect-strategy-spike/``.
Run locally; not part of the default compile-graph pipeline.
"""

from __future__ import annotations

import argparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir
from endorlabs.filters import main_context_filter
from endorlabs.utils.artifact_io import write_json
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.compile_graph.pipeline import (
    ProjectRef,
    namespace_slug,
    project_refs,
    project_rows_from_models,
)
from endorlabs.workflows.estate.collect.bounds import (
    count_for_progress,
    format_progress,
    is_list_truncated,
    resolve_max_pages,
)
from endorlabs.workflows.estate.filters.masks import DEP_METADATA_LIST_MASK

LOGGER = get_resource_logger(__name__)


def _session_user_slug(client: endorlabs.Client) -> str:
    who = str(client.whoami())
    local = who.split("@", 1)[0].strip().lower()
    safe = "".join(c if c.isalnum() or c in "._-" else "-" for c in local)
    return safe or "agent"


def spike_output_dir(*, user: str, context_dir: Path) -> Path:
    _ = user
    return default_runs_dir("collect-strategy-spike", context_dir)


def _dm_uuid(row: Any) -> str | None:
    if isinstance(row, dict):
        raw = row.get("uuid")
        return str(raw) if raw else None
    raw = getattr(row, "uuid", None)
    return str(raw) if raw else None


def _fetch_s0_project(
    client: endorlabs.Client,
    project: ProjectRef,
    *,
    max_pages: int | None,
    page_size: int,
    preflight_count: bool,
) -> tuple[int, int, set[str], bool]:
    filt = main_context_filter(f'spec.importer_data.project_uuid=="{project.uuid}"')
    expected = 0
    if preflight_count:
        cnt = count_for_progress(
            client.DependencyMetadata,
            project.namespace,
            resource_label="DependencyMetadata",
            filter_expr=filt,
            logger=LOGGER,
        )
        if cnt is not None:
            expected = cnt
    listed = client.DependencyMetadata.list(
        filter=filt,
        namespace=project.namespace,
        max_pages=max_pages,
        page_size=page_size,
        mask=DEP_METADATA_LIST_MASK,
    )
    n_rows = len(listed or [])
    truncated = is_list_truncated(n_rows, max_pages=max_pages, page_size=page_size)
    uuids: set[str] = set()
    for row in listed or []:
        uid = _dm_uuid(row)
        if uid:
            uuids.add(uid)
    return expected, n_rows, uuids, truncated


def strategy_s0_per_project_dm(
    client: endorlabs.Client,
    *,
    namespace: str,
    projects: list[ProjectRef],
    max_pages: int | None,
    page_size: int,
    max_workers: int = 16,
    preflight_count: bool = True,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    t_count = time.perf_counter()
    expected = 0
    rows = 0
    all_uuids: set[str] = set()
    truncated_projects = 0
    workers = max(1, min(max_workers, len(projects) or 1))
    completed = 0

    def _work(pref: ProjectRef) -> tuple[int, int, set[str], bool]:
        return _fetch_s0_project(
            client,
            pref,
            max_pages=max_pages,
            page_size=page_size,
            preflight_count=preflight_count,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_work, pref): pref for pref in projects}
        for fut in as_completed(futures):
            exp, n_rows, uuids, truncated = fut.result()
            expected += exp
            rows += n_rows
            all_uuids.update(uuids)
            if truncated:
                truncated_projects += 1
            completed += 1
            if completed % 100 == 0 or completed == len(projects):
                LOGGER.info(
                    "%s, %s",
                    format_progress("S0 projects", completed, len(projects)),
                    format_progress(
                        "S0 rows",
                        rows,
                        expected if preflight_count else None,
                    ),
                )

    count_ms = int((time.perf_counter() - t_count) * 1000)
    elapsed = time.perf_counter() - t0
    return {
        "strategy": "S0_per_project_dm",
        "count_ms": count_ms if preflight_count else None,
        "count_value": expected if preflight_count else None,
        "list_row_count": rows,
        "unique_dm_uuid_count": len(all_uuids),
        "parity_ok": not preflight_count or expected == 0 or rows == expected,
        "truncated_project_count": truncated_projects,
        "elapsed_s": round(elapsed, 3),
        "project_count": len(projects),
        "max_workers": workers,
    }


def strategy_s1_namespace_dm(
    client: endorlabs.Client,
    *,
    namespace: str,
    max_pages: int | None,
    page_size: int,
) -> dict[str, Any]:
    filt = main_context_filter()
    t_count = time.perf_counter()
    count_value = count_for_progress(
        client.DependencyMetadata,
        namespace,
        resource_label="DependencyMetadata",
        filter_expr=filt,
        logger=LOGGER,
    )
    count_ms = int((time.perf_counter() - t_count) * 1000)
    t_list = time.perf_counter()
    listed = client.DependencyMetadata.list(
        filter=filt,
        namespace=namespace,
        traverse=False,
        max_pages=max_pages,
        page_size=page_size,
        mask=DEP_METADATA_LIST_MASK,
    )
    list_ms = int((time.perf_counter() - t_list) * 1000)
    rows = len(listed or [])
    uuids = {_dm_uuid(r) for r in (listed or [])}
    uuids.discard(None)
    truncated = is_list_truncated(rows, max_pages=max_pages, page_size=page_size)
    return {
        "strategy": "S1_namespace_dm",
        "count_ms": count_ms,
        "list_ms": list_ms,
        "count_value": count_value,
        "list_row_count": rows,
        "unique_dm_uuid_count": len(uuids),
        "parity_ok": count_value is None or rows == count_value,
        "list_truncated": truncated,
        "elapsed_s": round((count_ms + list_ms) / 1000.0, 3),
    }


def strategy_s2_discover_only(
    client: endorlabs.Client,
    *,
    namespace: str,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    count_value = count_for_progress(
        client.Project,
        namespace,
        resource_label="Project",
        traverse=False,
        logger=LOGGER,
    )
    projects = client.Project.list(namespace=namespace, traverse=False)
    rows = project_rows_from_models(projects, namespace)
    elapsed = time.perf_counter() - t0
    return {
        "strategy": "S2_namespace_discover",
        "count_value": count_value,
        "list_row_count": len(rows),
        "parity_ok": count_value is None or len(rows) == count_value,
        "elapsed_s": round(elapsed, 3),
        "project_count": len(rows),
    }


def _compare_s0_s1(s0: dict[str, Any], s1: dict[str, Any]) -> dict[str, Any]:
    s0_rows = int(s0.get("list_row_count") or 0)
    s1_rows = int(s1.get("list_row_count") or 0)
    s0_unique = int(s0.get("unique_dm_uuid_count") or 0)
    s1_unique = int(s1.get("unique_dm_uuid_count") or 0)
    return {
        "row_count_delta_s0_minus_s1": s0_rows - s1_rows,
        "unique_uuid_delta_s0_minus_s1": s0_unique - s1_unique,
        "row_parity": s0_rows == s1_rows,
        "unique_uuid_parity": s0_unique == s1_unique,
        "faster_strategy": (
            "S1"
            if float(s1.get("elapsed_s") or 0) < float(s0.get("elapsed_s") or 0)
            else "S0"
            if float(s0.get("elapsed_s") or 0) < float(s1.get("elapsed_s") or 0)
            else "tie"
        ),
        "s0_elapsed_s": s0.get("elapsed_s"),
        "s1_elapsed_s": s1.get("elapsed_s"),
    }


def run_spike(
    client: endorlabs.Client,
    *,
    estate_tenant: str,
    namespace: str,
    output_dir: Path,
    sample_projects: int | None,
    max_pages: int | None,
    page_size: int,
    strategies: set[str],
    max_workers: int,
    preflight_count: bool,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    discover = client.Project.list(namespace=namespace, traverse=False)
    project_rows = project_rows_from_models(discover, namespace)
    refs = project_refs(project_rows, namespace)
    if sample_projects and sample_projects < len(refs):
        refs = refs[:sample_projects]

    strategy_results: list[dict[str, Any]] = []
    s0_result: dict[str, Any] | None = None
    s1_result: dict[str, Any] | None = None

    if "S2" in strategies:
        strategy_results.append(strategy_s2_discover_only(client, namespace=namespace))
    if "S1" in strategies:
        LOGGER.info("Running S1 namespace DM (full list, max_pages=%s)", max_pages)
        s1_result = strategy_s1_namespace_dm(
            client,
            namespace=namespace,
            max_pages=max_pages,
            page_size=page_size,
        )
        strategy_results.append(s1_result)
        write_json(
            str(output_dir / f"spike_S1_{namespace_slug(namespace)}.json"),
            s1_result,
            base_dir=output_dir,
        )
    if "S0" in strategies:
        LOGGER.info(
            "Running S0 per-project DM (%d projects, max_pages=%s, workers=%d)",
            len(refs),
            max_pages,
            max_workers,
        )
        s0_result = strategy_s0_per_project_dm(
            client,
            namespace=namespace,
            projects=refs,
            max_pages=max_pages,
            page_size=page_size,
            max_workers=max_workers,
            preflight_count=preflight_count,
        )
        strategy_results.append(s0_result)
        write_json(
            str(output_dir / f"spike_S0_{namespace_slug(namespace)}.json"),
            s0_result,
            base_dir=output_dir,
        )

    results: dict[str, Any] = {
        "estate_tenant": estate_tenant,
        "namespace": namespace,
        "namespace_slug": namespace_slug(namespace),
        "sample_projects": sample_projects,
        "max_pages": max_pages,
        "page_size": page_size,
        "project_count": len(refs),
        "strategies": strategy_results,
    }
    if s0_result and s1_result:
        results["s0_s1_comparison"] = _compare_s0_s1(s0_result, s1_result)

    label = "full" if max_pages is None else f"p{max_pages}"
    out_path = output_dir / f"spike_{label}_{namespace_slug(namespace)}.json"
    write_json(str(out_path), results, base_dir=output_dir)
    LOGGER.info("Wrote spike results: %s", out_path)
    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Benchmark DM collect strategies for one namespace"
    )
    p.add_argument("--tenant", required=True, help="Client tenant (estate root)")
    p.add_argument(
        "--namespace",
        required=True,
        help="Namespace to benchmark (child namespace recommended for bounded runs).",
    )
    p.add_argument("--context-dir", default=".endorlabs-context")
    p.add_argument(
        "--user",
        default=None,
        help=(
            "Deprecated: ignored; spike output is always "
            "workspace/runs/collect-strategy-spike/."
        ),
    )
    p.add_argument("--sample-projects", type=int, default=None)
    p.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="List page cap (0 = unlimited, fetch full DM set).",
    )
    p.add_argument("--page-size", type=int, default=500)
    p.add_argument(
        "--strategies",
        default="S1,S0",
        help="Comma-separated strategies to run (S0,S1,S2). Default: S1,S0",
    )
    p.add_argument("--max-workers", type=int, default=16, help="S0 parallel workers")
    p.add_argument(
        "--no-preflight-count",
        action="store_true",
        help="Skip per-project count calls in S0 (faster timing, no count parity).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    client = endorlabs.Client(tenant=args.tenant)
    try:
        user = args.user or _session_user_slug(client)
        out_dir = spike_output_dir(user=user, context_dir=Path(args.context_dir))
        strategies = {
            s.strip().upper() for s in args.strategies.split(",") if s.strip()
        }
        run_spike(
            client,
            estate_tenant=args.tenant,
            namespace=args.namespace,
            output_dir=out_dir,
            sample_projects=args.sample_projects,
            max_pages=resolve_max_pages(args.max_pages),
            page_size=args.page_size,
            strategies=strategies,
            max_workers=args.max_workers,
            preflight_count=not args.no_preflight_count,
        )
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
