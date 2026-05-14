#!/usr/bin/env python3
"""Find projects that have ScanResults whose ``meta.created_by`` matches a pattern.

Follows repository list guidance:

- ``docs/rules-of-engagement/list-query-performance.md`` — scope, selective
  filters, pagination vs server work, debugging slow lists (timeouts, narrow scope).
- ``docs/rules-of-engagement/namespace-traversal.md`` — tenant-wide lists: prefer
  ``traverse=True`` with **selective** filters; avoid tiny ``page_size`` unless
  needed; use ``max_pages`` to cap client-side pagination.

**Default strategy** ``concurrent``: SDK ``ScanResult.list(traverse=True,
concurrent=True)`` — one namespace discovery pass, then **parallel** per-namespace
``ScanResult`` lists (see ``facade.ResourceRuntimeFacade._list_concurrent``).
Namespaces passed to ``--exclude-namespace`` are still dropped **client-side**
from matching rows.

**Alternate strategy** ``traverse``: a single tenant-root ``ScanResult`` stream
with ``traverse=True`` only (no ``concurrent``). Use if the concurrent path fails
or times out.

**Alternate strategy** ``shard``: manual ``Namespace.list`` plus a thread pool
(useful if you need to **skip** namespaces before any ``ScanResult`` call, e.g.
to avoid querying excluded namespaces at all).

Auth: ``ENDOR_TOKEN`` or ``ENDOR_API_CREDENTIALS_*`` (see ``README.md``); use
``uv run --env-file .env``.

Examples (PowerShell)::

    uv run --env-file .env python devtools/find_projects_by_scan_created_by.py ^
      --namespace tenant.example --timeout 90 --max-pages 50

    uv run --env-file .env python devtools/find_projects_by_scan_created_by.py ^
      --list-strategy traverse --timeout 120 --max-pages 20

    uv run --env-file .env python devtools/find_projects_by_scan_created_by.py ^
      --list-strategy shard --parallel 8 --max-pages 30

``--namespace`` defaults to ``ENDOR_NAMESPACE`` when set, else ``tenant.example``
(list root). Replace with your tenant. Do not commit secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import endorlabs
from endorlabs import F
from endorlabs.core.types import ListParameters
from endorlabs.utils.parallel import ConcurrentNamespaceQueryError


def _namespace_names_under_root(client: endorlabs.Client, root: str) -> list[str]:
    """Return canonical namespace paths (including *root*) for all descendants."""
    all_ns = client.Namespace.list(
        namespace=root,
        traverse=True,
        max_pages=None,
    )
    names: list[str] = []
    for ns_obj in all_ns:
        if ns_obj.spec and ns_obj.spec.full_name:
            names.append(ns_obj.spec.full_name)
        elif ns_obj.tenant_meta and ns_obj.tenant_meta.namespace and ns_obj.meta:
            parent_ns = ns_obj.tenant_meta.namespace
            if ns_obj.meta.name:
                names.append(f"{parent_ns}.{ns_obj.meta.name}")
            else:
                names.append(parent_ns)
        elif ns_obj.tenant_meta and ns_obj.tenant_meta.namespace:
            names.append(ns_obj.tenant_meta.namespace)

    if root not in names:
        names.insert(0, root)
    return sorted(set(names), key=lambda s: (s.count("."), s))


def _is_excluded(ns: str, excluded: tuple[str, ...]) -> bool:
    return any(ns == ex or ns.startswith(f"{ex}.") for ex in excluded)


@dataclass
class _Agg:
    scan_rows: int = 0
    sample_created_by: str | None = None
    sample_scan_uuids: list[str] = field(default_factory=list)


def _default_pattern() -> str:
    # Typical API-key ``meta.created_by`` lines end with a stable ``@api-key``
    # suffix; tighten with ``--created-by-regex`` for your tenant.
    return r".*@api-key$"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--namespace",
        "-n",
        default=os.environ.get("ENDOR_NAMESPACE", "tenant.example"),
        help=(
            "Tenant namespace for Client(tenant=...) and list roots "
            "(default: ENDOR_NAMESPACE env or tenant.example)."
        ),
    )
    p.add_argument(
        "--tenant",
        default=None,
        help="Deprecated alias for --namespace; if set, overrides --namespace.",
    )
    p.add_argument(
        "--list-strategy",
        choices=("concurrent", "traverse", "shard"),
        default="concurrent",
        help=(
            "concurrent: ScanResult.list(traverse=True, concurrent=True) "
            "(default). traverse: single traverse stream. shard: manual "
            "Namespace list + thread pool (skips excluded NS before ScanResult)."
        ),
    )
    p.add_argument(
        "--exclude-namespace",
        action="append",
        default=None,
        help=(
            "Exclude this namespace and any child (repeatable). "
            "When omitted, no namespaces are excluded by default."
        ),
    )
    p.add_argument(
        "--created-by-regex",
        default=_default_pattern(),
        help="Regex for meta.created_by (API ``matches`` operator).",
    )
    p.add_argument(
        "--from-date",
        default=None,
        help="Optional ISO8601 lower bound on meta.create_time (reduces work).",
    )
    p.add_argument(
        "--to-date",
        default=None,
        help="Optional ISO8601 upper bound on meta.create_time.",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help=(
            "Cap ScanResult list pages (SDK client bound only). "
            "concurrent and shard: per-namespace cap. "
            "traverse: total pages for the single traverse stream."
        ),
    )
    p.add_argument(
        "--page-size",
        type=int,
        default=None,
        help=(
            "Page size for ScanResult lists; omit to use API default (preferred "
            "unless you have a specific need — see namespace-traversal.md)."
        ),
    )
    p.add_argument(
        "--parallel",
        type=int,
        default=8,
        help=(
            "concurrent: max_workers for SDK parallel namespace lists. "
            "shard: thread pool size (default 8)."
        ),
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=None,
        help=(
            "HTTP read timeout in seconds for each Client (default: Client default "
            "60 or ENDOR_REQUEST_TIMEOUT). Use a finite timeout so stalled lists fail "
            "fast (list-query-performance.md)."
        ),
    )
    p.add_argument(
        "--mask",
        default=(
            "uuid,meta.parent_uuid,meta.created_by,meta.create_time,"
            "tenant_meta.namespace,spec.status,spec.type,context.id,context.type"
        ),
        help="Comma-separated field mask for ScanResult list.",
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Write JSON report to this path (UTF-8).",
    )
    p.add_argument(
        "--max-sample-scans",
        type=int,
        default=3,
        help="Keep up to N sample scan UUIDs per project in the report.",
    )
    p.add_argument(
        "--no-project-details",
        action="store_true",
        help="Skip Project.get per match (faster; omit repo URL and app links).",
    )
    return p.parse_args(argv)


def _client_kwargs(*, timeout: float | None) -> dict[str, Any]:
    if timeout is None:
        return {}
    return {"timeout": float(timeout)}


def _resolve_project_meta_names(
    rows: list[dict[str, Any]],
    *,
    root: str,
    ckws: dict[str, Any],
    max_workers: int,
) -> None:
    """Set project_meta_name on each row via Project.get (in-place)."""

    def work(entry: dict[str, Any]) -> None:
        ns = entry["namespace"]
        uid = entry["project_uuid"]
        client = endorlabs.Client(tenant=root, **ckws)
        try:
            proj = client.Project.get(uid, namespace=ns)
            entry["project_meta_name"] = (
                proj.meta.name if proj.meta and proj.meta.name else None
            )
        except Exception:
            entry["project_meta_name"] = None
        finally:
            client.close()

    if not rows:
        return
    workers = max(1, min(max_workers, len(rows)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, rows))


def _build_scan_list_params(
    *,
    traverse: bool,
    created_by_filter: str,
    mask: str,
    page_size: int | None,
    from_date: str | None,
    to_date: str | None,
) -> ListParameters:
    lp_kwargs: dict[str, Any] = {
        "traverse": traverse,
        "filter": created_by_filter,
        "mask": mask,
    }
    if page_size is not None:
        lp_kwargs["page_size"] = page_size
    if from_date:
        lp_kwargs["from_date"] = from_date
    if to_date:
        lp_kwargs["to_date"] = to_date
    return ListParameters(**lp_kwargs)  # pyright: ignore[reportCallIssue]


def _ingest_one_scan(
    sr: Any,
    *,
    default_ns: str | None,
    excluded: tuple[str, ...],
    per_project: dict[tuple[str, str], _Agg],
    max_sample_scans: int,
) -> None:
    if isinstance(sr, dict):
        tm = sr.get("tenant_meta") or {}
        tmn = (
            str(tm["namespace"])
            if isinstance(tm, dict) and tm.get("namespace")
            else default_ns
        )
        meta = sr.get("meta") or {}
        parent = (
            meta.get("parent_uuid")
            if isinstance(meta, dict)
            else None
        )
        created_by = (
            meta.get("created_by")
            if isinstance(meta, dict)
            else None
        )
        scan_uuid = sr.get("uuid")
    else:
        tmn = (
            sr.tenant_meta.namespace
            if sr.tenant_meta and sr.tenant_meta.namespace
            else default_ns
        )
        parent = sr.meta.parent_uuid if sr.meta else None
        created_by = sr.meta.created_by if sr.meta else None
        scan_uuid = sr.uuid
    if not tmn or _is_excluded(tmn, excluded):
        return
    if not parent:
        return
    key = (tmn, parent)
    bucket = per_project[key]
    bucket.scan_rows += 1
    if bucket.sample_created_by is None and created_by:
        bucket.sample_created_by = str(created_by)
    if len(bucket.sample_scan_uuids) < max_sample_scans and scan_uuid is not None:
        bucket.sample_scan_uuids.append(str(scan_uuid))


def _scan_one_namespace_shard(
    *,
    root_tenant: str,
    target_ns: str,
    list_params: ListParameters,
    max_pages: int | None,
    ckws: dict[str, Any],
) -> list[Any]:
    """Dedicated client per thread (httpx client is not assumed thread-safe)."""
    client = endorlabs.Client(tenant=root_tenant, **ckws)
    try:
        return list(
            client.ScanResult.list_iter(
                namespace=target_ns,
                list_params=list_params,
                max_pages=max_pages,
            )
        )
    finally:
        client.close()


def _run_traverse(
    *,
    root: str,
    excluded: tuple[str, ...],
    list_params: ListParameters,
    max_pages: int | None,
    ckws: dict[str, Any],
    max_sample_scans: int,
) -> tuple[dict[tuple[str, str], _Agg], dict[str, str]]:
    per_project: dict[tuple[str, str], _Agg] = defaultdict(_Agg)
    ns_errors: dict[str, str] = {}
    client = endorlabs.Client(tenant=root, **ckws)
    try:
        for sr in client.ScanResult.list_iter(
            namespace=root,
            list_params=list_params,
            max_pages=max_pages,
        ):
            _ingest_one_scan(
                sr,
                default_ns=None,
                excluded=excluded,
                per_project=per_project,
                max_sample_scans=max_sample_scans,
            )
    except Exception as exc:
        ns_errors["<traverse>"] = f"{type(exc).__name__}: {exc}"
    finally:
        client.close()
    return per_project, ns_errors


def _run_concurrent(
    *,
    root: str,
    excluded: tuple[str, ...],
    list_params: ListParameters,
    max_pages: int | None,
    ckws: dict[str, Any],
    max_workers: int,
    max_sample_scans: int,
) -> tuple[dict[tuple[str, str], _Agg], dict[str, str]]:
    """SDK traverse + concurrent: parallel ScanResult lists per namespace."""
    per_project: dict[tuple[str, str], _Agg] = defaultdict(_Agg)
    ns_errors: dict[str, str] = {}
    client = endorlabs.Client(tenant=root, **ckws)
    try:
        rows = client.ScanResult.list(
            traverse=True,
            concurrent=True,
            max_workers=max(1, max_workers),
            namespace=root,
            list_params=list_params,
            max_pages=max_pages,
        )
        for sr in rows:
            _ingest_one_scan(
                sr,
                default_ns=None,
                excluded=excluded,
                per_project=per_project,
                max_sample_scans=max_sample_scans,
            )
    except ConcurrentNamespaceQueryError as exc:
        for ns, err in exc.failures:
            ns_errors[ns] = f"{type(err).__name__}: {err}"
    except Exception as exc:
        ns_errors["<concurrent>"] = f"{type(exc).__name__}: {exc}"
    finally:
        client.close()
    return per_project, ns_errors


def _run_shard(
    *,
    root: str,
    excluded: tuple[str, ...],
    list_params: ListParameters,
    max_pages: int | None,
    parallel: int,
    ckws: dict[str, Any],
    max_sample_scans: int,
) -> tuple[
    dict[tuple[str, str], _Agg],
    dict[str, str],
    list[str],
]:
    orchestrator = endorlabs.Client(tenant=root, **ckws)
    try:
        all_namespaces = _namespace_names_under_root(orchestrator, root)
    finally:
        orchestrator.close()

    targets = [n for n in all_namespaces if not _is_excluded(n, excluded)]
    per_project: dict[tuple[str, str], _Agg] = defaultdict(_Agg)
    ns_errors: dict[str, str] = {}

    def work(ns: str) -> tuple[str, list[Any] | None, str | None]:
        try:
            rows = _scan_one_namespace_shard(
                root_tenant=root,
                target_ns=ns,
                list_params=list_params,
                max_pages=max_pages,
                ckws=ckws,
            )
            return ns, rows, None
        except Exception as exc:
            return ns, None, f"{type(exc).__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=max(1, parallel)) as pool:
        futures = {pool.submit(work, ns): ns for ns in targets}
        for fut in as_completed(futures):
            ns, rows, err = fut.result()
            if err:
                ns_errors[ns] = err
                continue
            assert rows is not None
            for sr in rows:
                _ingest_one_scan(
                    sr,
                    default_ns=ns,
                    excluded=excluded,
                    per_project=per_project,
                    max_sample_scans=max_sample_scans,
                )

    return per_project, ns_errors, all_namespaces


def main(argv: list[str] | None = None) -> int:
    """CLI entry: aggregate matching ScanResults into a JSON report."""
    args = _parse_args(argv)
    root = args.tenant if args.tenant is not None else args.namespace
    if args.exclude_namespace:
        excluded = tuple(sorted(set(args.exclude_namespace)))
    else:
        excluded = ()

    created_by_filter = str(F("meta.created_by").matches(args.created_by_regex))
    ckws = _client_kwargs(timeout=args.timeout)

    strategy: str = args.list_strategy
    all_namespaces: list[str] | None = None

    if strategy == "traverse":
        lp = _build_scan_list_params(
            traverse=True,
            created_by_filter=created_by_filter,
            mask=args.mask,
            page_size=args.page_size,
            from_date=args.from_date,
            to_date=args.to_date,
        )
        per_project, ns_errors = _run_traverse(
            root=root,
            excluded=excluded,
            list_params=lp,
            max_pages=args.max_pages,
            ckws=ckws,
            max_sample_scans=args.max_sample_scans,
        )
    elif strategy == "concurrent":
        lp = _build_scan_list_params(
            traverse=False,
            created_by_filter=created_by_filter,
            mask=args.mask,
            page_size=args.page_size,
            from_date=args.from_date,
            to_date=args.to_date,
        )
        per_project, ns_errors = _run_concurrent(
            root=root,
            excluded=excluded,
            list_params=lp,
            max_pages=args.max_pages,
            ckws=ckws,
            max_workers=args.parallel,
            max_sample_scans=args.max_sample_scans,
        )
    else:
        lp = _build_scan_list_params(
            traverse=False,
            created_by_filter=created_by_filter,
            mask=args.mask,
            page_size=args.page_size,
            from_date=args.from_date,
            to_date=args.to_date,
        )
        per_project, ns_errors, all_namespaces = _run_shard(
            root=root,
            excluded=excluded,
            list_params=lp,
            max_pages=args.max_pages,
            parallel=args.parallel,
            ckws=ckws,
            max_sample_scans=args.max_sample_scans,
        )

    projects_out = [
        {
            "namespace": tmn,
            "project_uuid": proj_uuid,
            "app_scan_history_url": (
                f"https://app.endorlabs.com/t/{tmn}/projects/{proj_uuid}/"
                "versions/default/scan-history"
            ),
            "matching_scan_count": agg.scan_rows,
            "sample_created_by": agg.sample_created_by,
            "sample_scan_uuids": agg.sample_scan_uuids,
        }
        for (tmn, proj_uuid), agg in sorted(
            per_project.items(), key=lambda kv: (-kv[1].scan_rows, kv[0][0], kv[0][1])
        )
    ]

    if not args.no_project_details and projects_out:
        _resolve_project_meta_names(
            projects_out,
            root=root,
            ckws=ckws,
            max_workers=args.parallel,
        )

    report: dict[str, Any] = {
        "purpose": (
            "Projects with ScanResults matching the created_by regex (typically "
            "duplicate CI/API-key scans vs platform scans). Use app_scan_history_url "
            "to confirm and remediate redundant triggers."
        ),
        "list_strategy": strategy,
        "namespace": root,
        "excluded_namespaces": list(excluded),
        "created_by_filter": created_by_filter,
        "namespaces_total": len(all_namespaces) if all_namespaces is not None else None,
        "namespaces_queried": len(all_namespaces) if strategy == "shard" else None,
        "max_workers": args.parallel if strategy in ("concurrent", "shard") else None,
        "namespaces_failed": len(ns_errors),
        "projects_with_matches": len(projects_out),
        "projects": projects_out,
        "namespace_errors": ns_errors,
        "performance_notes": (
            "See docs/rules-of-engagement/list-query-performance.md "
            "and namespace-traversal.md. Regex on meta.created_by may be a "
            "heavy list key - validate latency vs endorctl api list if unsure."
        ),
    }

    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        out_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        sys.stderr.write(f"Wrote {out_path}\n")
    sys.stdout.write(text)
    return 1 if ns_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
