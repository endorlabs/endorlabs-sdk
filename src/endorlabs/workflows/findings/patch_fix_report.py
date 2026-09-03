"""Findings fixable by a patch, aggregated by package + current version.

Mirrors the row shape and sort order of the estate version-cardinality report
(``endorlabs.workflows.estate.analyze.cardinality.export``) but sources rows
from ``Finding.spec.target_dependency_*`` / ``spec.fixing_patch`` instead of
``DependencyMetadata`` usage counts.

Design notes (verified against real tenants before writing this module — see
``.endorlabs/tasks/scratch/`` probes, not committed):

- ``spec.fixing_patch.endor_patch_available`` is the platform's own "Endor
  Patch" signal — Endor Labs republished a hardened build for this exact
  finding. This is narrower than the ``FINDING_TAGS_FIX_AVAILABLE`` tag (true
  on a minority of fix-available findings; skews toward ecosystems where
  Endor curates patches, e.g. Maven) — a deliberate, documented product
  concept, not a bug.
- ``--gate`` controls which findings are fetched: ``any`` (default) is the
  union of both signals — the broadest, single-query dataset, so downstream
  filtering (patch-available vs. patch-to-request, reachable vs. not) can be
  done post-hoc on one export instead of re-querying. ``endor-patch`` and
  ``fix-available`` narrow to one signal only.
- "Patches to request" has **no dedicated platform field** (verified — no
  request/requestable field or enum exists on ``Finding`` or
  ``VersionUpgrade`` in the generated models). This module *infers* it as
  fix-available-or-has-an-upgrade-path but **not** Endor-patch-available —
  reported as ``patches_to_request_count`` in the summary, explicitly labeled
  as inferred, not an official platform category.
- ``spec.fixing_upgrades.upgrade_list`` is recorded on the Finding as a
  computed upgrade-impact path (direct-dep bump). This report does **not**
  group on it — family keys are ``target_dependency_package_name`` +
  ``target_dependency_version`` (Endor Patches dashboard grain).
- ``has_upgrade_path_count`` in ``signal_breakdown`` still counts findings
  with a populated upgrade list. Rollup rows include findings that have a
  target coordinate even when that list is empty.
- ``--reachability`` is applied client-side (not pushed into the server
  filter) — the ``FilterExpression`` DSL only supports negation on
  ``exists()`` clauses, not general boolean negation of ``contains``
  clauses, so "no reachability tag present" has no safe server-side
  expression here. Every detail row still carries its own reachability
  columns regardless of this flag, for post-hoc pivoting.
- Finding pulls exclude dismissed rows (``spec.dismiss != true``), matching
  the product findings UI default exception filter.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.context.paths import (
    task_activity_dir,
    tasks_dir,
)
from endorlabs.filters import FINDING_CATEGORY_VULNERABILITY
from endorlabs.workflows.findings.patch_core import (
    FINDING_MASK,
    GATE_CHOICES,
    NOT_DISMISSED_CLAUSE,
    REACHABILITY_CHOICES,
    build_finding_filter,
    compute_signal_breakdown,
    discover_and_list,
    extract_patch_rows,
    filter_by_reachability,
)
from endorlabs.workflows.findings.patch_fix_columns import (
    PATCH_FIX_FINDING_DETAIL_COLUMNS,
    PATCH_FIX_REPORT_COLUMNS,
)
from endorlabs.workflows.findings.patch_fix_types import (
    PatchFixReportResult,
    PatchFixReportStats,
)
from endorlabs.workflows.tabular import TabularExport, write_table

if TYPE_CHECKING:
    from endorlabs import Client

logger = logging.getLogger(__name__)

# Re-exported for historical imports / docs (collection core lives in patch_core).
_ = (FINDING_MASK, NOT_DISMISSED_CLAUSE)


def _namespace_slug(namespace: str) -> str:
    """Local slug helper — do not import estate's ``namespace_slug`` (layer ban)."""
    cleaned = namespace.strip().rstrip(".")
    return cleaned.replace(".", "_") if cleaned else "unknown"


def _rollup_patch_fix_rows(
    namespace: str,
    detail_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse detail rows to one row per ``(package_name, current_version)``."""
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for row in detail_rows:
        key = (row["package_name"], row["current_version"])
        bucket = groups.setdefault(
            key,
            {
                "finding_uuids": set(),
                "patch_versions": set(),
                "project_uuids": set(),
                "path_count": 0,
            },
        )
        bucket["finding_uuids"].add(row["finding_uuid"])
        bucket["path_count"] += 1
        if row["patch_version"]:
            bucket["patch_versions"].add(row["patch_version"])
        if row["project_uuid"]:
            bucket["project_uuids"].add(row["project_uuid"])

    rows: list[dict[str, Any]] = []
    for (package_name, current_version), bucket in sorted(groups.items()):
        patch_versions: set[str] = bucket["patch_versions"]
        patch_version = min(patch_versions) if patch_versions else ""
        rows.append(
            {
                "namespace": namespace,
                "package_name": package_name,
                "current_version": current_version,
                "patch_version": patch_version,
                "finding_count": len(bucket["finding_uuids"]),
                "distinct_patch_version_count": len(patch_versions),
                "distinct_upgrade_path_count": bucket["path_count"],
                "project_count": len(bucket["project_uuids"]),
            }
        )
    return rows


def build_patch_fix_report(
    client: Client,
    namespace: str,
    *,
    finding_categories: Sequence[str] = (FINDING_CATEGORY_VULNERABILITY,),
    severities: Sequence[str] | None = None,
    gate: str = "any",
    reachability: str = "any",
    max_project_pages: int | None = None,
    max_pages: int | None = None,
    max_workers: int = 12,
    include_finding_detail: bool = False,
) -> PatchFixReportResult:
    """Findings fixable by a patch, rolled up by package + current version.

    ``gate="any"`` (default) fetches the union of both patch/fix signals —
    the broadest single-query dataset. ``reachability`` narrows client-side
    (``"any"``/``"reachable"``/``"unreachable"``); every returned row still
    carries its own reachability columns regardless, for post-hoc pivoting.
    ``result.signal_breakdown`` reports counts confirming the empirical
    relationship between the patch/fix/reachability signals (see module
    docstring) — it is computed over all gated findings.
    """
    if gate not in GATE_CHOICES:
        msg = f"gate must be one of {GATE_CHOICES}, got {gate!r}"
        raise ValueError(msg)
    if reachability not in REACHABILITY_CHOICES:
        msg = (
            f"reachability must be one of {REACHABILITY_CHOICES}, got {reachability!r}"
        )
        raise ValueError(msg)

    finding_filter = build_finding_filter(finding_categories, severities, gate=gate)
    try:
        shards, findings = discover_and_list(
            client,
            namespace,
            finding_filter,
            max_project_pages=max_project_pages,
            max_pages=max_pages,
            max_workers=max_workers,
        )
    except Exception as exc:
        return PatchFixReportResult(
            status="error",
            message=f"Project discovery failed: {exc}",
            errors=[str(exc)],
            stats=PatchFixReportStats(namespace=namespace),
        )

    if not shards:
        return PatchFixReportResult(
            status="success",
            message="No projects discovered.",
            stats=PatchFixReportStats(namespace=namespace),
        )

    findings = filter_by_reachability(findings, reachability)
    detail_rows = extract_patch_rows(findings)
    rollup_rows = _rollup_patch_fix_rows(namespace, detail_rows)
    signal_breakdown = compute_signal_breakdown(findings)
    fixable_finding_count = len({row["finding_uuid"] for row in detail_rows})
    stats = PatchFixReportStats(
        namespace=namespace,
        project_count=len(shards),
        finding_count=len(findings),
        fixable_finding_count=fixable_finding_count,
        package_group_count=len(rollup_rows),
    )
    result = PatchFixReportResult(
        status="success",
        message=(
            f"{len(rollup_rows)} package/version group(s) from "
            f"{fixable_finding_count} finding(s) with a target dependency "
            f"across {stats.project_count} project(s)."
        ),
        stats=stats,
        table=TabularExport(rows=rollup_rows, columns=list(PATCH_FIX_REPORT_COLUMNS)),
        signal_breakdown=signal_breakdown,
    )
    if include_finding_detail:
        # Prefer wire namespace on the Finding; fall back to estate root.
        detail_out: list[dict[str, Any]] = [
            {**row, "namespace": row.get("namespace") or namespace}
            for row in detail_rows
        ]
        result.finding_detail = TabularExport(
            rows=detail_out,
            columns=list(PATCH_FIX_FINDING_DETAIL_COLUMNS),
        )
    return result


def _summary_dict(result: PatchFixReportResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "message": result.message,
        "errors": result.errors,
        "namespace": result.stats.namespace,
        "project_count": result.stats.project_count,
        "finding_count": result.stats.finding_count,
        "fixable_finding_count": result.stats.fixable_finding_count,
        "package_group_count": result.stats.package_group_count,
        "signal_breakdown": result.signal_breakdown,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Build argparse parser for this workflow CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Findings fixable by a patch, aggregated by package name + "
            "current version (mirrors export-version's sort order). Default "
            "--gate any fetches the union of the Endor Patch catalog and the "
            "fix-available tag in one query."
        ),
    )
    parser.add_argument(
        "--namespace",
        "-n",
        default=os.environ.get("ENDOR_NAMESPACE"),
        help="Estate root namespace (default: ENDOR_NAMESPACE).",
    )
    parser.add_argument(
        "--output",
        "-o",
        help=(
            "Output CSV path for the package/version rollup (default: "
            f"{tasks_dir().as_posix()}/<slug>-<YYYY-MM-DD>/estate/"
            "patch_fix_report_<slug>.csv)."
        ),
    )
    parser.add_argument(
        "--finding-detail-output",
        help="Optional CSV for one row per (finding, upgrade candidate).",
    )
    parser.add_argument(
        "--finding-category",
        action="append",
        dest="finding_categories",
        help=(
            "Finding category to include (repeatable; default "
            f"{FINDING_CATEGORY_VULNERABILITY})."
        ),
    )
    parser.add_argument(
        "--severity",
        action="append",
        dest="severities",
        help="Severity level to include (repeatable; default: all).",
    )
    parser.add_argument(
        "--gate",
        choices=GATE_CHOICES,
        default="any",
        help=(
            "Which patch/fix signal(s) to fetch: 'any' (default; union of "
            "both), 'endor-patch' (spec.fixing_patch.endor_patch_available "
            "only), or 'fix-available' (FINDING_TAGS_FIX_AVAILABLE only)."
        ),
    )
    parser.add_argument(
        "--reachability",
        choices=REACHABILITY_CHOICES,
        default="any",
        help=(
            "Client-side reachability narrowing: 'any' (default, no "
            "filter), 'reachable' (REACHABLE_FUNCTION or "
            "POTENTIALLY_REACHABLE_FUNCTION tag present), or 'unreachable' "
            "(neither tag present)."
        ),
    )
    parser.add_argument(
        "--max-project-pages",
        type=int,
        default=None,
        help="Max project-discovery pages (default: unlimited).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max Finding list pages per project (default: unlimited).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=12,
        help="Concurrent per-project shard workers (default: 12).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI: build the patch-fix report and write CSV output."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    if not args.namespace:
        sys.stderr.write("error: --namespace or ENDOR_NAMESPACE is required\n")
        return 2

    import endorlabs

    if args.output:
        output_path = Path(args.output)
    else:
        slug = _namespace_slug(args.namespace)
        output_path = (
            task_activity_dir(args.namespace, "estate") / f"patch_fix_report_{slug}.csv"
        )

    with endorlabs.Client(tenant=args.namespace) as client:
        result = build_patch_fix_report(
            client,
            args.namespace,
            finding_categories=tuple(
                args.finding_categories or (FINDING_CATEGORY_VULNERABILITY,)
            ),
            severities=args.severities,
            gate=args.gate,
            reachability=args.reachability,
            max_project_pages=args.max_project_pages,
            max_pages=args.max_pages,
            max_workers=args.max_workers,
            include_finding_detail=bool(args.finding_detail_output),
        )

    if result.ok:
        write_table(result.table, output_path)
        if args.finding_detail_output:
            # Always write when requested (including empty) so the summary path exists.
            write_table(result.finding_detail, args.finding_detail_output)

    summary = _summary_dict(result)
    if result.ok:
        summary["output"] = str(output_path)
        if args.finding_detail_output:
            summary["finding_detail_output"] = args.finding_detail_output
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
