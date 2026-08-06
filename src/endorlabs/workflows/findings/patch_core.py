"""Shared Finding collection core for patch-fix / Endor Patches reports.

Both the estate ``patch-fix-report`` extractor and the executive packet
narrative collector use this module for filters, list pulls, signal flags,
and detail-row extraction. Aggregation and HTML rendering stay product-specific.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from endorlabs.filters import MAIN_CONTEXT_CLAUSE
from endorlabs.workflows.findings.prf_analysis import list_findings_tenant
from endorlabs.workflows.wire_access import dict_str, nested_dict

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.tools.list_sharding import ProjectShard

FINDING_MASK = (
    "uuid,meta.name,meta.description,tenant_meta.namespace,spec.project_uuid,"
    "spec.level,spec.extra_key,spec.target_dependency_package_name,"
    "spec.target_dependency_version,spec.fixing_patch,spec.fixing_upgrades,"
    "spec.finding_tags,spec.finding_metadata"
)

# Product findings UI: exception filter "not dismissed" (app uses NOT_EQUAL on
# spec.dismiss / true). Keep this in the list filter so counts match the UI.
NOT_DISMISSED_CLAUSE = "spec.dismiss != true"

_ENDOR_PATCH_AVAILABLE = "spec.fixing_patch.endor_patch_available==true"
_FIX_AVAILABLE_TAG = "spec.finding_tags contains FINDING_TAGS_FIX_AVAILABLE"
_REACHABLE_FUNCTION_TAG = "FINDING_TAGS_REACHABLE_FUNCTION"
_POTENTIALLY_REACHABLE_FUNCTION_TAG = "FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"
_UNREACHABLE_FUNCTION_TAG = "FINDING_TAGS_UNREACHABLE_FUNCTION"
_REACHABLE_DEPENDENCY_TAG = "FINDING_TAGS_REACHABLE_DEPENDENCY"
_POTENTIALLY_REACHABLE_DEPENDENCY_TAG = "FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY"
_UNREACHABLE_DEPENDENCY_TAG = "FINDING_TAGS_UNREACHABLE_DEPENDENCY"

GATE_CHOICES: tuple[str, ...] = ("any", "endor-patch", "fix-available")
REACHABILITY_CHOICES: tuple[str, ...] = ("any", "reachable", "unreachable")

_REACH_FLAG_KEYS: tuple[str, ...] = (
    "reachable_function",
    "potentially_reachable_function",
    "unreachable_function",
    "reachable_dependency",
    "potentially_reachable_dependency",
    "unreachable_dependency",
)

_SEVERITY_ALIASES: dict[str, str] = {
    "CRITICAL": "FINDING_LEVEL_CRITICAL",
    "HIGH": "FINDING_LEVEL_HIGH",
    "MEDIUM": "FINDING_LEVEL_MEDIUM",
    "LOW": "FINDING_LEVEL_LOW",
}


def _severity_enum(token: str) -> str:
    upper = token.strip().upper()
    return _SEVERITY_ALIASES.get(upper, token)


def build_finding_filter(
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

    Always excludes dismissed findings (``spec.dismiss != true``), matching
    the product findings UI.
    """
    parts = [MAIN_CONTEXT_CLAUSE, NOT_DISMISSED_CLAUSE]
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


def finding_tags(finding: dict[str, Any]) -> list[str]:
    """Return ``spec.finding_tags`` as a list of strings."""
    tags = nested_dict(finding, "spec").get("finding_tags")
    if isinstance(tags, list):
        return [str(tag) for tag in cast("list[Any]", tags)]
    return []


def upgrade_list_items(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Return typed upgrade-list entries from a Finding ``spec`` dict."""
    raw = nested_dict(spec, "fixing_upgrades").get("upgrade_list")
    if not isinstance(raw, list):
        return []
    return [item for item in cast("list[Any]", raw) if isinstance(item, dict)]


def finding_signal_flags(finding: dict[str, Any]) -> dict[str, bool]:
    """Compute the patch/fix/reachability booleans carried by one finding."""
    spec = nested_dict(finding, "spec")
    tags = finding_tags(finding)
    upgrades = upgrade_list_items(spec)
    return {
        "fix_available": "FINDING_TAGS_FIX_AVAILABLE" in tags,
        "endor_patch_available": bool(
            nested_dict(spec, "fixing_patch").get("endor_patch_available")
        ),
        "has_upgrade_path": bool(upgrades),
        "reachable_function": _REACHABLE_FUNCTION_TAG in tags,
        "potentially_reachable_function": _POTENTIALLY_REACHABLE_FUNCTION_TAG in tags,
        "unreachable_function": _UNREACHABLE_FUNCTION_TAG in tags,
        "reachable_dependency": _REACHABLE_DEPENDENCY_TAG in tags,
        "potentially_reachable_dependency": (
            _POTENTIALLY_REACHABLE_DEPENDENCY_TAG in tags
        ),
        "unreachable_dependency": _UNREACHABLE_DEPENDENCY_TAG in tags,
    }


def patch_status(flags: dict[str, bool]) -> str:
    """Map Finding signals to Available vs inferred To Request.

    ``to_request_inferred`` is not a platform enum — see patch_fix_report
    module docstring.
    """
    if flags["endor_patch_available"]:
        return "available"
    if flags["fix_available"] or flags["has_upgrade_path"]:
        return "to_request_inferred"
    return "other"


def severity_label(level: str) -> str:
    """Strip ``FINDING_LEVEL_`` prefix from a severity enum string."""
    raw = (level or "").strip()
    if raw.startswith("FINDING_LEVEL_"):
        return raw.removeprefix("FINDING_LEVEL_")
    return raw


def vuln_fields(finding: dict[str, Any]) -> dict[str, str]:
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
        alias_list = [str(a) for a in cast("list[Any]", aliases) if a]
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


def filter_by_reachability(
    findings: Sequence[dict[str, Any]],
    reachability: str,
) -> list[dict[str, Any]]:
    """Client-side reachability filter (no safe server-side negation for this)."""
    if reachability == "any":
        return list(findings)
    kept: list[dict[str, Any]] = []
    for finding in findings:
        tags = finding_tags(finding)
        is_reachable = (
            _REACHABLE_FUNCTION_TAG in tags
            or _POTENTIALLY_REACHABLE_FUNCTION_TAG in tags
        )
        if (reachability == "reachable" and is_reachable) or (
            reachability == "unreachable" and not is_reachable
        ):
            kept.append(finding)
    return kept


def compute_signal_breakdown(findings: Sequence[dict[str, Any]]) -> dict[str, int]:
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
    counts = {key: 0 for key in _REACH_FLAG_KEYS}
    no_reachability_tag = 0

    for finding in findings:
        flags = finding_signal_flags(finding)
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
        any_reach = False
        for key in _REACH_FLAG_KEYS:
            if flags[key]:
                counts[key] += 1
                any_reach = True
        if not any_reach:
            no_reachability_tag += 1

    return {
        "total_findings": len(findings),
        "endor_patch_available_count": endor_patch,
        "fix_available_tag_count": fix_tag,
        "both_endor_patch_and_fix_tag_count": both,
        "neither_endor_patch_nor_fix_tag_count": neither,
        "has_upgrade_path_count": has_upgrade_path,
        "patches_to_request_count": patches_to_request,
        "reachable_function_count": counts["reachable_function"],
        "potentially_reachable_function_count": counts[
            "potentially_reachable_function"
        ],
        "unreachable_function_count": counts["unreachable_function"],
        "reachable_dependency_count": counts["reachable_dependency"],
        "potentially_reachable_dependency_count": counts[
            "potentially_reachable_dependency"
        ],
        "unreachable_dependency_count": counts["unreachable_dependency"],
        "no_reachability_tag_count": no_reachability_tag,
    }


def _detail_row_from_upgrade_item(
    finding: dict[str, Any],
    *,
    flags: dict[str, bool],
    vuln: dict[str, str],
    item: dict[str, Any],
) -> dict[str, Any] | None:
    package_name = dict_str(item, "direct_dependency_name")
    if not package_name:
        return None
    spec = nested_dict(finding, "spec")
    tenant_meta = nested_dict(finding, "tenant_meta")
    return {
        "namespace": dict_str(tenant_meta, "namespace"),
        "project_uuid": dict_str(spec, "project_uuid"),
        "finding_uuid": dict_str(finding, "uuid"),
        "finding_type_name": vuln["finding_type_name"],
        "vuln_id": vuln["vuln_id"],
        "vuln_aliases": vuln["vuln_aliases"],
        "vuln_summary": vuln["vuln_summary"],
        "severity": severity_label(dict_str(spec, "level")),
        "package_name": package_name,
        "current_version": dict_str(item, "from_version"),
        "patch_version": dict_str(item, "to_version"),
        "target_dependency_package_name": dict_str(
            spec, "target_dependency_package_name"
        ),
        "target_dependency_version": dict_str(spec, "target_dependency_version"),
        "endor_patch_available": flags["endor_patch_available"],
        "fix_available": flags["fix_available"],
        "patch_status": patch_status(flags),
        "reachable_function": flags["reachable_function"],
        "potentially_reachable_function": flags["potentially_reachable_function"],
        "unreachable_function": flags["unreachable_function"],
        "reachable_dependency": flags["reachable_dependency"],
        "potentially_reachable_dependency": flags["potentially_reachable_dependency"],
        "unreachable_dependency": flags["unreachable_dependency"],
        "upgrade_risk": dict_str(item, "upgrade_risk"),
    }


def _detail_row_from_target_dependency(
    finding: dict[str, Any],
) -> dict[str, Any] | None:
    """Fallback row when no ``upgrade_list`` entry exists (same schema)."""
    spec = nested_dict(finding, "spec")
    pkg = dict_str(spec, "target_dependency_package_name")
    if not pkg:
        return None
    flags = finding_signal_flags(finding)
    vuln = vuln_fields(finding)
    tenant_meta = nested_dict(finding, "tenant_meta")
    target_version = dict_str(spec, "target_dependency_version")
    return {
        "namespace": dict_str(tenant_meta, "namespace"),
        "project_uuid": dict_str(spec, "project_uuid"),
        "finding_uuid": dict_str(finding, "uuid"),
        "finding_type_name": vuln["finding_type_name"],
        "vuln_id": vuln["vuln_id"],
        "vuln_aliases": vuln["vuln_aliases"],
        "vuln_summary": vuln["vuln_summary"],
        "severity": severity_label(dict_str(spec, "level")),
        "package_name": pkg,
        "current_version": target_version,
        "patch_version": "",
        "target_dependency_package_name": pkg,
        "target_dependency_version": target_version,
        "endor_patch_available": flags["endor_patch_available"],
        "fix_available": flags["fix_available"],
        "patch_status": patch_status(flags),
        "reachable_function": flags["reachable_function"],
        "potentially_reachable_function": flags["potentially_reachable_function"],
        "unreachable_function": flags["unreachable_function"],
        "reachable_dependency": flags["reachable_dependency"],
        "potentially_reachable_dependency": flags["potentially_reachable_dependency"],
        "unreachable_dependency": flags["unreachable_dependency"],
        "upgrade_risk": "",
    }


def extract_patch_rows(
    findings: Sequence[dict[str, Any]],
    *,
    allow_target_dependency_fallback: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    """Flatten findings into detail rows; optionally fall back to target dependency.

    Prefer ``fixing_upgrades.upgrade_list`` rows (``rollup_mode="upgrade_list"``).
    When *allow_target_dependency_fallback* is true and no finding has a
    computed upgrade path, emit one row per finding from
    ``target_dependency_package_name`` /
    ``target_dependency_version`` (``rollup_mode="target_dependency_fallback"``).

    Fallback rows use the same schema as upgrade-list rows (including
    ``upgrade_risk``, empty when unknown).

    When *allow_target_dependency_fallback* is false, findings without an
    upgrade path contribute no rows (``rollup_mode`` remains ``"upgrade_list"``).
    """
    detail_rows: list[dict[str, Any]] = []
    for finding in findings:
        spec = nested_dict(finding, "spec")
        upgrades = upgrade_list_items(spec)
        if not upgrades:
            continue
        flags = finding_signal_flags(finding)
        vuln = vuln_fields(finding)
        for item in upgrades:
            row = _detail_row_from_upgrade_item(
                finding, flags=flags, vuln=vuln, item=item
            )
            if row is not None:
                detail_rows.append(row)
    if detail_rows or not allow_target_dependency_fallback:
        return detail_rows, "upgrade_list"

    fallback: list[dict[str, Any]] = []
    for finding in findings:
        row = _detail_row_from_target_dependency(finding)
        if row is not None:
            fallback.append(row)
    return fallback, "target_dependency_fallback"


def discover_and_list(
    client: Client,
    namespace: str,
    finding_filter: str,
    *,
    max_project_pages: int | None = None,
    max_pages: int | None = None,
    max_workers: int = 12,
) -> tuple[list[ProjectShard], list[dict[str, Any]]]:
    """Discover project shards and list patch-gated findings with ``FINDING_MASK``.

    Returns ``(shards, findings)``. Callers that need reachability narrowing
    should run :func:`filter_by_reachability` on *findings* afterward.
    """
    shards = list(
        client.Query.Project.discover(
            namespace,
            traverse=True,
            max_pages=max_project_pages,
            exclude_sbom=True,
        ).project_shards()
    )
    if not shards:
        return [], []
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
    return shards, findings
