"""Findings fixable by a patch, aggregated by package + current version.

Mirrors the row shape and sort order of the estate version-cardinality report
(``endorlabs.workflows.estate.analyze.cardinality.export``) but sources rows
from ``Finding.spec.fixing_upgrades``/``spec.fixing_patch`` instead of
``DependencyMetadata`` usage counts.

Design notes (verified against real tenants before writing this module — see
``.endorlabs-context/workspace/runs/scratch/`` probes, not committed):

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
- ``spec.fixing_upgrades.upgrade_list`` (``direct_dependency_name``,
  ``from_version``, ``to_version``, ``upgrade_risk``) lives directly on the
  Finding and supplies the actual upgrade target — no second API call, no
  join to ``VersionUpgrade`` needed. (An earlier version of this module tried
  a ``VersionUpgrade``-based join; ``VersionUpgrade.spec.
  finding_fixing_upgrades``/``other_finding_info.fixed_findings`` were empty
  in practice on every tenant probed. This field is simpler and populated.)
- Rollup rows only cover findings where ``fixing_upgrades.upgrade_list`` is
  non-empty (a target version is required to report one) — some
  fix-available/Endor-patch-available findings do not yet have a computed
  upgrade path. The ``signal_breakdown`` summary counts *all* gated findings
  regardless, so that population isn't silently dropped from the picture.
- ``--reachability`` is applied client-side (not pushed into the server
  filter) — the ``FilterExpression`` DSL only supports negation on
  ``exists()`` clauses, not general boolean negation of ``contains``
  clauses, so "no reachability tag present" has no safe server-side
  expression here. Every detail row still carries its own reachability
  columns regardless of this flag, for post-hoc pivoting.
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

from endorlabs.context.paths import default_runs_dir
from endorlabs.filters import FINDING_CATEGORY_VULNERABILITY, MAIN_CONTEXT_CLAUSE
from endorlabs.workflows.findings.patch_fix_columns import (
    PATCH_FIX_FINDING_DETAIL_COLUMNS,
    PATCH_FIX_REPORT_COLUMNS,
)
from endorlabs.workflows.findings.patch_fix_types import (
    PatchFixReportResult,
    PatchFixReportStats,
)
from endorlabs.workflows.findings.prf_analysis import list_findings_tenant
from endorlabs.workflows.tabular import TabularExport, write_table
from endorlabs.workflows.wire_access import dict_str, nested_dict

if TYPE_CHECKING:
    from endorlabs import Client

logger = logging.getLogger(__name__)

FINDING_MASK = (
    "uuid,meta.name,meta.description,tenant_meta.namespace,spec.project_uuid,"
    "spec.level,spec.extra_key,spec.target_dependency_package_name,"
    "spec.target_dependency_version,spec.fixing_patch,spec.fixing_upgrades,"
    "spec.finding_tags,spec.finding_metadata"
)
_ENDOR_PATCH_AVAILABLE = "spec.fixing_patch.endor_patch_available==true"
_FIX_AVAILABLE_TAG = "spec.finding_tags contains FINDING_TAGS_FIX_AVAILABLE"
_REACHABLE_FUNCTION_TAG = "FINDING_TAGS_REACHABLE_FUNCTION"
_POTENTIALLY_REACHABLE_FUNCTION_TAG = "FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"

GATE_CHOICES: tuple[str, ...] = ("any", "endor-patch", "fix-available")
REACHABILITY_CHOICES: tuple[str, ...] = ("any", "reachable", "unreachable")

_SEVERITY_ALIASES: dict[str, str] = {
    "CRITICAL": "FINDING_LEVEL_CRITICAL",
    "HIGH": "FINDING_LEVEL_HIGH",
    "MEDIUM": "FINDING_LEVEL_MEDIUM",
    "LOW": "FINDING_LEVEL_LOW",
}


def _namespace_slug(namespace: str) -> str:
    """Local slug helper — do not import estate's ``namespace_slug`` (layer ban)."""
    cleaned = namespace.strip().rstrip(".")
    return cleaned.replace(".", "_") if cleaned else "unknown"


def _severity_enum(token: str) -> str:
    upper = token.strip().upper()
    return _SEVERITY_ALIASES.get(upper, token)


def _build_finding_filter(
    finding_categories: Sequence[str],
    severities: Sequence[str] | None,
    *,
    gate: str,
) -> str:
    """Main-context Finding filter for categories/severities + the patch gate.

    ``gate="any"`` (default) is the union of both patch/fix signals — the
    broadest single-query dataset, so patch-available vs. patch-to-request
    (and reachable vs. not) can be sliced post-hoc from one export.
    ``"endor-patch"`` / ``"fix-available"`` narrow to one signal only.
    """
    parts = [MAIN_CONTEXT_CLAUSE]
    if finding_categories:
        clause = " or ".join(
            f"spec.finding_categories contains [{c}]" for c in finding_categories
        )
        parts.append(f"({clause})" if len(finding_categories) > 1 else clause)
    if severities:
        levels = [_severity_enum(s) for s in severities]
        clause = " or ".join(f"spec.level=={lvl}" for lvl in levels)
        parts.append(f"({clause})" if len(levels) > 1 else clause)
    if gate == "endor-patch":
        parts.append(_ENDOR_PATCH_AVAILABLE)
    elif gate == "fix-available":
        parts.append(_FIX_AVAILABLE_TAG)
    else:
        parts.append(f"({_ENDOR_PATCH_AVAILABLE} or {_FIX_AVAILABLE_TAG})")
    return " and ".join(parts)


def _finding_tags(finding: dict[str, Any]) -> list[str]:
    tags = nested_dict(finding, "spec").get("finding_tags")
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    return []


def _finding_signal_flags(finding: dict[str, Any]) -> dict[str, bool]:
    """Compute the patch/fix/reachability booleans carried by one finding."""
    spec = nested_dict(finding, "spec")
    tags = _finding_tags(finding)
    upgrade_list = nested_dict(spec, "fixing_upgrades").get("upgrade_list") or []
    return {
        "fix_available": "FINDING_TAGS_FIX_AVAILABLE" in tags,
        "endor_patch_available": bool(
            nested_dict(spec, "fixing_patch").get("endor_patch_available")
        ),
        "has_upgrade_path": bool(upgrade_list),
        "reachable_function": _REACHABLE_FUNCTION_TAG in tags,
        "potentially_reachable_function": _POTENTIALLY_REACHABLE_FUNCTION_TAG in tags,
    }


def _patch_status(flags: dict[str, bool]) -> str:
    """Map Finding signals to Available vs inferred To Request.

    ``to_request_inferred`` is not a platform enum — see module docstring.
    """
    if flags["endor_patch_available"]:
        return "available"
    if flags["fix_available"] or flags["has_upgrade_path"]:
        return "to_request_inferred"
    return "other"


def _severity_label(level: str) -> str:
    raw = (level or "").strip()
    if raw.startswith("FINDING_LEVEL_"):
        return raw.removeprefix("FINDING_LEVEL_")
    return raw


def _vuln_fields(finding: dict[str, Any]) -> dict[str, str]:
    """Prefer advisory id from nested Vuln metadata over generic finding type name."""
    meta = nested_dict(finding, "meta")
    spec = nested_dict(finding, "spec")
    finding_type = dict_str(meta, "name")
    description = dict_str(meta, "description")
    extra_key = dict_str(spec, "extra_key")
    vuln = nested_dict(nested_dict(spec, "finding_metadata"), "vulnerability")
    vuln_meta = nested_dict(vuln, "meta")
    vuln_spec = nested_dict(vuln, "spec")
    vuln_id = dict_str(vuln_meta, "name") or extra_key
    aliases = vuln_spec.get("aliases")
    alias_list: list[str] = []
    if isinstance(aliases, list):
        alias_list = [str(a) for a in aliases if a]
    summary = dict_str(vuln_meta, "description") or dict_str(vuln_spec, "summary")
    if not summary and description:
        # Often "GHSA-…: title" when nested vuln is masked away.
        summary = description
    if not vuln_id and description:
        vuln_id = description.split(":", 1)[0].strip()
    return {
        "finding_type_name": finding_type,
        "vuln_id": vuln_id,
        "vuln_aliases": ";".join(alias_list),
        "vuln_summary": summary,
    }


def _filter_by_reachability(
    findings: Sequence[dict[str, Any]],
    reachability: str,
) -> list[dict[str, Any]]:
    """Client-side reachability filter (no safe server-side negation for this)."""
    if reachability == "any":
        return list(findings)
    kept: list[dict[str, Any]] = []
    for finding in findings:
        tags = _finding_tags(finding)
        is_reachable = (
            _REACHABLE_FUNCTION_TAG in tags
            or _POTENTIALLY_REACHABLE_FUNCTION_TAG in tags
        )
        if (reachability == "reachable" and is_reachable) or (
            reachability == "unreachable" and not is_reachable
        ):
            kept.append(finding)
    return kept


def _compute_signal_breakdown(findings: Sequence[dict[str, Any]]) -> dict[str, int]:
    """Counts confirming the patch/fix/reachability set relationships empirically.

    ``patches_to_request`` is an *inferred* category (fix-available or has a
    computed upgrade path, but not Endor-patch-available) — there is no
    dedicated platform field for it.
    """
    endor_patch = 0
    fix_tag = 0
    both = 0
    neither = 0
    has_upgrade_path = 0
    patches_to_request = 0
    reachable = 0
    potentially_reachable = 0
    no_reachability_tag = 0

    for finding in findings:
        flags = _finding_signal_flags(finding)
        if flags["endor_patch_available"]:
            endor_patch += 1
        if flags["fix_available"]:
            fix_tag += 1
        if flags["endor_patch_available"] and flags["fix_available"]:
            both += 1
        if not flags["endor_patch_available"] and not flags["fix_available"]:
            neither += 1
        if flags["has_upgrade_path"]:
            has_upgrade_path += 1
        if not flags["endor_patch_available"] and (
            flags["fix_available"] or flags["has_upgrade_path"]
        ):
            patches_to_request += 1
        if flags["reachable_function"]:
            reachable += 1
        if flags["potentially_reachable_function"]:
            potentially_reachable += 1
        if (
            not flags["reachable_function"]
            and not flags["potentially_reachable_function"]
        ):
            no_reachability_tag += 1

    return {
        "total_findings": len(findings),
        "endor_patch_available_count": endor_patch,
        "fix_available_tag_count": fix_tag,
        "both_endor_patch_and_fix_tag_count": both,
        "neither_endor_patch_nor_fix_tag_count": neither,
        "has_upgrade_path_count": has_upgrade_path,
        "patches_to_request_count": patches_to_request,
        "reachable_function_count": reachable,
        "potentially_reachable_function_count": potentially_reachable,
        "no_reachability_tag_count": no_reachability_tag,
    }


def _extract_patch_rows(findings: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten each finding's ``fixing_upgrades.upgrade_list`` into detail rows.

    A finding with no computed upgrade path yet contributes no rows (see
    ``_compute_signal_breakdown`` for counts over the full gated population,
    including findings without a computed path).
    """
    detail_rows: list[dict[str, Any]] = []
    for finding in findings:
        spec = nested_dict(finding, "spec")
        upgrade_list = nested_dict(spec, "fixing_upgrades").get("upgrade_list") or []
        if not upgrade_list:
            continue
        flags = _finding_signal_flags(finding)
        project_uuid = dict_str(spec, "project_uuid")
        finding_uuid = dict_str(finding, "uuid")
        target_package = dict_str(spec, "target_dependency_package_name")
        target_version = dict_str(spec, "target_dependency_version")
        tenant_meta = nested_dict(finding, "tenant_meta")
        severity = _severity_label(dict_str(spec, "level"))
        finding_ns = dict_str(tenant_meta, "namespace")
        vuln = _vuln_fields(finding)
        detail_rows.extend(
            {
                "namespace": finding_ns,
                "project_uuid": project_uuid,
                "finding_uuid": finding_uuid,
                "finding_type_name": vuln["finding_type_name"],
                "vuln_id": vuln["vuln_id"],
                "vuln_aliases": vuln["vuln_aliases"],
                "vuln_summary": vuln["vuln_summary"],
                "severity": severity,
                "package_name": dict_str(item, "direct_dependency_name"),
                "current_version": dict_str(item, "from_version"),
                "patch_version": dict_str(item, "to_version"),
                "target_dependency_package_name": target_package,
                "target_dependency_version": target_version,
                "endor_patch_available": flags["endor_patch_available"],
                "fix_available": flags["fix_available"],
                "patch_status": _patch_status(flags),
                "reachable_function": flags["reachable_function"],
                "potentially_reachable_function": flags[
                    "potentially_reachable_function"
                ],
                "upgrade_risk": dict_str(item, "upgrade_risk"),
            }
            for item in upgrade_list
            if isinstance(item, dict) and dict_str(item, "direct_dependency_name")
        )
    return detail_rows


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
        patch_version = sorted(patch_versions)[0] if patch_versions else ""
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
    docstring) — it is computed over all gated findings, not just those with
    a computed upgrade path.
    """
    if gate not in GATE_CHOICES:
        msg = f"gate must be one of {GATE_CHOICES}, got {gate!r}"
        raise ValueError(msg)
    if reachability not in REACHABILITY_CHOICES:
        msg = (
            f"reachability must be one of {REACHABILITY_CHOICES}, got {reachability!r}"
        )
        raise ValueError(msg)

    try:
        shards = client.Query.Project.discover(
            namespace,
            traverse=True,
            max_pages=max_project_pages,
            exclude_sbom=True,
        ).project_shards()
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

    finding_filter = _build_finding_filter(finding_categories, severities, gate=gate)
    findings = list_findings_tenant(
        client,
        namespace,
        finding_filter,
        mask=FINDING_MASK,
        max_pages=max_pages,
        max_workers=max_workers,
        max_project_pages=max_project_pages,
        shards=shards,
    )
    findings = _filter_by_reachability(findings, reachability)

    detail_rows = _extract_patch_rows(findings)
    rollup_rows = _rollup_patch_fix_rows(namespace, detail_rows)
    signal_breakdown = _compute_signal_breakdown(findings)
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
            f"{fixable_finding_count} finding(s) with a computed upgrade path "
            f"across {stats.project_count} project(s)."
        ),
        stats=stats,
        table=TabularExport(rows=rollup_rows, columns=list(PATCH_FIX_REPORT_COLUMNS)),
        signal_breakdown=signal_breakdown,
    )
    if include_finding_detail:
        # Prefer wire namespace on the Finding; fall back to estate root.
        detail_out = [
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
            "Output CSV path for the package/version rollup "
            f"(default: {default_runs_dir('patch-fix-report').as_posix()}/"
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
            default_runs_dir("patch-fix-report") / f"patch_fix_report_{slug}.csv"
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
