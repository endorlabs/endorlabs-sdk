#!/usr/bin/env python3
"""Main-context PackageVersion resolution report (CSV).

Lists PackageVersion rows with context.type==CONTEXT_TYPE_MAIN across a tenant
(including child namespaces), then enriches each row with concurrent Finding /
DependencyMetadata counts and Project metadata.

Does not use the graph Query join from ewok query.package_resolution.json —
related data is fetched with separate scoped count/get calls per PackageVersion.
"""

from __future__ import annotations

import argparse
import csv
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment
from endorlabs.filters import pv_main_context_filter

RUN_BUCKET = "package-resolution"

CSV_COLUMNS = [
    "Namespace",
    "PackageVersion UUID",
    "PackageVersion Name",
    "PackageVersion Ecosystem",
    "Num Approximated Vulns",
    "Num Vulns",
    "Num Approximated Dependencies",
    "Num Dependencies",
    "Resolution Error Category",
    "Resolution Error Type",
    "Fixable",
    "Fixable Notes",
    "Full Success",
    "Unresolved Success",
    "Resolved Success",
    "Call Graph Success",
    "Resolution Error (Unresolved)",
    "Resolution Error (Resolved)",
    "Resolution Error (Call Graph)",
    "Resolution Error Target (Unresolved)",
    "Resolution Error Target (Resolved)",
    "Resolution Error Target (Call Graph)",
    "Resolution Error Operation (Unresolved)",
    "Resolution Error Operation (Resolved)",
    "Resolution Error Operation (Call Graph)",
    "Scan State",
    "Scan Time",
    "Analytic Time",
    "Disable Automated Scan",
    "Project UUID",
    "Project Name",
    "Project Tags",
    "Endor URL",
]

PV_MASK = (
    "uuid,meta.name,tenant_meta.namespace,spec.project_uuid,spec.ecosystem,"
    "spec.resolution_errors,processing_status"
)


def _attr(obj: Any, *names: str, default: Any = None) -> Any:
    cur = obj
    for name in names:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(name, default)
        else:
            cur = getattr(cur, name, default)
    return cur


def _enum_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _error_present(status: Any) -> bool:
    """True when the API included a resolution status object for this stage."""
    if status is None:
        return False
    if isinstance(status, dict):
        return bool(status)
    return True


def _resolution_errors(pv: Any) -> Any:
    return _attr(pv, "spec", "resolution_errors")


def _status_field(errors: Any, kind: str, field: str) -> str:
    status = _attr(errors, kind)
    if not status:
        return ""
    value = _attr(status, field)
    text = _enum_str(value)
    if field == "status_error" and text == "STATUS_ERROR_UNSPECIFIED":
        return ""
    return text


def _pick_best_match(errors: Any) -> Any:
    """Prefer unresolved → resolved → call_graph for error_analysis_best_match.

    ``error_analysis_best_match`` lives on each ``V1ResolutionStatus`` (unresolved /
    resolved / call_graph), not on ``resolution_errors`` itself.
    """
    if not errors:
        return None
    for kind in ("unresolved", "resolved", "call_graph"):
        status = _attr(errors, kind)
        if not status:
            continue
        best = _attr(status, "error_analysis_best_match")
        if best:
            return best
    return None


def _success_flags(errors: Any) -> dict[str, str]:
    unresolved = _error_present(_attr(errors, "unresolved"))
    resolved = _error_present(_attr(errors, "resolved"))
    call_graph = _error_present(_attr(errors, "call_graph"))

    unresolved_success = "FALSE" if unresolved else "TRUE"

    if unresolved:
        resolved_success = "N/A"
    elif resolved:
        resolved_success = "FALSE"
    else:
        resolved_success = "TRUE"

    if unresolved or resolved:
        call_graph_success = "N/A"
    elif call_graph:
        call_graph_success = "FALSE"
    else:
        call_graph_success = "TRUE"

    full_success = "TRUE" if not any([unresolved, resolved, call_graph]) else "FALSE"
    return {
        "Full Success": full_success,
        "Unresolved Success": unresolved_success,
        "Resolved Success": resolved_success,
        "Call Graph Success": call_graph_success,
    }


def _endor_url(namespace: str, project_uuid: str) -> str:
    if not namespace or not project_uuid:
        return ""
    return (
        f"https://app.endorlabs.com/t/{namespace}/projects/{project_uuid}"
        "/versions/default/inventory/packages"
    )


def _fmt_time(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _fmt_tags(tags: Any) -> str:
    if not tags:
        return ""
    if isinstance(tags, (list, tuple)):
        return ";".join(str(t) for t in tags)
    return str(tags)


class ProjectCache:
    def __init__(self, client: endorlabs.Client) -> None:
        super().__init__()
        self._client = client
        self._lock = threading.Lock()
        self._by_uuid: dict[str, tuple[str, str]] = {}

    def get(self, project_uuid: str, namespace: str) -> tuple[str, str]:
        if not project_uuid:
            return ("", "")
        with self._lock:
            cached = self._by_uuid.get(project_uuid)
            if cached is not None:
                return cached
        name, tags = "", ""
        try:
            project = self._client.Project.get(
                project_uuid, namespace=namespace or None
            )
        except Exception:
            project = None
        if project is not None:
            name = str(_attr(project, "meta", "name") or "")
            tags = _fmt_tags(_attr(project, "meta", "tags"))
        with self._lock:
            self._by_uuid[project_uuid] = (name, tags)
            return self._by_uuid[project_uuid]


def _count_related(client: endorlabs.Client, pv: Any) -> dict[str, int]:
    uuid = str(_attr(pv, "uuid") or "")
    ns = str(
        _attr(pv, "tenant_meta", "namespace") or getattr(pv, "namespace", "") or ""
    )
    if not uuid or not ns:
        return {
            "Num Approximated Vulns": 0,
            "Num Vulns": 0,
            "Num Approximated Dependencies": 0,
            "Num Dependencies": 0,
        }

    approx_vuln_filter = (
        f'meta.parent_uuid=="{uuid}" and spec.approximation==true and '
        "spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]"
    )
    vuln_filter = (
        f'meta.parent_uuid=="{uuid}" and '
        "spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]"
    )
    approx_dep_filter = (
        f'spec.importer_data.package_version_uuid=="{uuid}" and '
        "spec.dependency_data.approximation==true"
    )
    dep_filter = f'spec.importer_data.package_version_uuid=="{uuid}"'

    return {
        "Num Approximated Vulns": client.Finding.count(
            namespace=ns, filter=approx_vuln_filter
        ),
        "Num Vulns": client.Finding.count(namespace=ns, filter=vuln_filter),
        "Num Approximated Dependencies": client.DependencyMetadata.count(
            namespace=ns, filter=approx_dep_filter
        ),
        "Num Dependencies": client.DependencyMetadata.count(
            namespace=ns, filter=dep_filter
        ),
    }


def build_row(
    client: endorlabs.Client,
    pv: Any,
    project_cache: ProjectCache,
) -> dict[str, Any]:
    ns = str(
        _attr(pv, "tenant_meta", "namespace") or getattr(pv, "namespace", None) or ""
    )
    uuid = str(_attr(pv, "uuid") or "")
    name = str(_attr(pv, "meta", "name") or "")
    ecosystem = _enum_str(_attr(pv, "spec", "ecosystem"))
    project_uuid = str(_attr(pv, "spec", "project_uuid") or "")
    errors = _resolution_errors(pv)
    best = _pick_best_match(errors)
    counts = _count_related(client, pv)
    project_name, project_tags = project_cache.get(project_uuid, ns)
    processing = _attr(pv, "processing_status")

    row: dict[str, Any] = {
        "Namespace": ns,
        "PackageVersion UUID": uuid,
        "PackageVersion Name": name,
        "PackageVersion Ecosystem": ecosystem,
        **counts,
        "Resolution Error Category": _enum_str(_attr(best, "error_category")),
        "Resolution Error Type": str(_attr(best, "matching_rule") or ""),
        "Fixable": (
            ""
            if _attr(best, "fixable") is None
            else str(bool(_attr(best, "fixable"))).upper()
        ),
        "Fixable Notes": str(_attr(best, "fixable_notes") or ""),
        **_success_flags(errors),
        "Resolution Error (Unresolved)": _status_field(
            errors, "unresolved", "status_error"
        ),
        "Resolution Error (Resolved)": _status_field(
            errors, "resolved", "status_error"
        ),
        "Resolution Error (Call Graph)": _status_field(
            errors, "call_graph", "status_error"
        ),
        "Resolution Error Target (Unresolved)": _status_field(
            errors, "unresolved", "target"
        ),
        "Resolution Error Target (Resolved)": _status_field(
            errors, "resolved", "target"
        ),
        "Resolution Error Target (Call Graph)": _status_field(
            errors, "call_graph", "target"
        ),
        "Resolution Error Operation (Unresolved)": _status_field(
            errors, "unresolved", "operation"
        ),
        "Resolution Error Operation (Resolved)": _status_field(
            errors, "resolved", "operation"
        ),
        "Resolution Error Operation (Call Graph)": _status_field(
            errors, "call_graph", "operation"
        ),
        "Scan State": _enum_str(_attr(processing, "scan_state")),
        "Scan Time": _fmt_time(_attr(processing, "scan_time")),
        "Analytic Time": _fmt_time(_attr(processing, "analytic_time")),
        "Disable Automated Scan": (
            ""
            if _attr(processing, "disable_automated_scan") is None
            else str(bool(_attr(processing, "disable_automated_scan"))).upper()
        ),
        "Project UUID": project_uuid,
        "Project Name": project_name,
        "Project Tags": project_tags,
        "Endor URL": _endor_url(ns, project_uuid),
    }
    return row


def collect_rows(
    client: endorlabs.Client,
    *,
    tenant: str,
    max_workers: int,
    max_inflight: int,
) -> list[dict[str, Any]]:
    project_cache = ProjectCache(client)
    rows: list[dict[str, Any]] = []
    pending: dict[Future[dict[str, Any]], None] = {}
    seen = 0
    done = 0

    print(
        f"Listing main-context PackageVersions for tenant={tenant} "
        f"(traverse=True, workers={max_workers})…",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for pv in client.PackageVersion.list_iter(
            traverse=True,
            filter=pv_main_context_filter(),
            mask=PV_MASK,
        ):
            seen += 1
            if seen % 50 == 0:
                print(f"listed {seen} PackageVersions…", flush=True)
            while len(pending) >= max_inflight:
                finished = next(as_completed(pending.keys()))
                rows.append(finished.result())
                del pending[finished]
                done += 1
                if done % 25 == 0:
                    print(f"enriched {done}/{seen} PackageVersions", flush=True)
            pending[pool.submit(build_row, client, pv, project_cache)] = None

        for fut in as_completed(list(pending.keys())):
            rows.append(fut.result())
            done += 1
            if done % 25 == 0 or done == seen:
                print(f"enriched {done}/{seen} PackageVersions", flush=True)

    print(f"Collected {len(rows)} rows (listed {seen})", flush=True)
    rows.sort(
        key=lambda r: (
            str(r.get("Namespace") or ""),
            str(r.get("PackageVersion Name") or ""),
            str(r.get("PackageVersion UUID") or ""),
        )
    )
    return rows


def write_csv(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate main-context PackageVersion resolution CSV for a tenant "
            "(traverse child namespaces; concurrent related-object counts)."
        )
    )
    parser.add_argument(
        "--tenant",
        required=True,
        help="Tenant root namespace for Client(tenant=...) and traverse list.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace/runs/package-resolution/...).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=16,
        help="Thread pool size for related-object API calls (default: 16).",
    )
    parser.add_argument(
        "--max-inflight",
        type=int,
        default=64,
        help="Max in-flight PackageVersion enrichments (default: 64).",
    )
    parser.add_argument(
        "--json-summary",
        type=Path,
        default=None,
        help="Optional JSON summary path.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Client request timeout in seconds (default: 120).",
    )
    return parser.parse_args(argv)


def build_summary(
    tenant: str, rows: list[dict[str, Any]], csv_path: Path
) -> dict[str, Any]:
    return {
        "tenant": tenant,
        "row_count": len(rows),
        "csv": str(csv_path),
        "namespaces": sorted(
            {str(r.get("Namespace") or "") for r in rows if r.get("Namespace")}
        ),
        "full_success_count": sum(1 for r in rows if r.get("Full Success") == "TRUE"),
        "full_failure_count": sum(1 for r in rows if r.get("Full Success") == "FALSE"),
        "unresolved_manifest_false": sum(
            1 for r in rows if r.get("Unresolved Success") == "FALSE"
        ),
        "dependency_resolution_false": sum(
            1 for r in rows if r.get("Resolved Success") == "FALSE"
        ),
        "reachability_false": sum(
            1 for r in rows if r.get("Call Graph Success") == "FALSE"
        ),
        "no_best_match": sum(
            1
            for r in rows
            if r.get("Full Success") == "FALSE"
            and not (r.get("Resolution Error Type") or "").strip()
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output
    if output is None:
        safe = sanitize_path_segment(args.tenant)
        output = default_runs_dir(RUN_BUCKET) / f"{safe}-package-resolution.csv"

    client = endorlabs.Client(tenant=args.tenant, timeout=float(args.timeout))
    try:
        rows = collect_rows(
            client,
            tenant=args.tenant,
            max_workers=max(1, args.max_workers),
            max_inflight=max(1, args.max_inflight),
        )
    finally:
        client.close()

    write_csv(rows, output)
    summary = build_summary(args.tenant, rows, output)
    if args.json_summary:
        args.json_summary.parent.mkdir(parents=True, exist_ok=True)
        args.json_summary.write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    print(f"Wrote {output}")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
