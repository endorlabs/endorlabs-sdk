"""Portable dependency-resolution coverage analysis and dated report CLI."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs import Client
from endorlabs.context.paths import default_reports_subdir, sanitize_path_segment
from endorlabs.filters import pv_main_context_filter
from endorlabs.utils.path_safety import safe_write_text

RUN_BUCKET = "depr-coverage"
MAIN = str(pv_main_context_filter())
PROJECT_MASK = "uuid,meta.name,tenant_meta.namespace"
PV_MASK = "uuid,meta.name,tenant_meta.namespace,spec.project_uuid,spec.ecosystem"
PV_ERROR_MASK = f"{PV_MASK},spec.relative_path,spec.resolution_errors"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else value.model_dump(mode="json")


def _child_of(tenant: str, namespace: str | None) -> str:
    parts = (namespace or "").split(".")
    if parts and parts[0] == tenant:
        return parts[1] if len(parts) > 1 else "(root)"
    return "(root)"


def _ecosystem(pv: dict[str, Any], spec: dict[str, Any]) -> str:
    ecosystem = spec.get("ecosystem")
    name = str((pv.get("meta") or {}).get("name") or "")
    if isinstance(ecosystem, str) and ecosystem.startswith("ECOSYSTEM_"):
        return ecosystem.removeprefix("ECOSYSTEM_").lower()
    if ecosystem:
        return str(ecosystem).lower()
    return name.split("://", 1)[0] if "://" in name else "unknown"


def _best_match(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    analysis = item.get("error_analysis_best_match") or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except (TypeError, json.JSONDecodeError):
            analysis = {}
    if not isinstance(analysis, dict):
        analysis = {}
    return {
        "matching_rule": str(analysis.get("matching_rule") or "no_best_match"),
        "fixable": analysis.get("fixable"),
        "fixable_notes": str(analysis.get("fixable_notes") or ""),
        "error_category": str(analysis.get("error_category") or ""),
    }


def theme_bucket(rule: str, eco: str, category: str) -> tuple[str, str]:
    """Classify one failed PackageVersion into an executive remediation theme."""
    rule = rule or "no_best_match"
    eco = (eco or "unknown").lower()
    category = category or ""
    if (
        rule
        in {
            "maven_private_repo_artifact_absent",
            "maven_artifact_not_found_due_to_absent",
            "maven_artifact_not_found",
            "maven_artifact_not_resolved",
            "could_not_find_artifact",
        }
        and eco == "maven"
    ):
        return (
            "maven_private_artifactory",
            "Configure Maven Artifactory/Nexus for private parent POMs and artifacts",
        )
    if rule in {
        "temp_pom_not_found",
        "java_build_failed_with_exception",
        "maven_invalid_pom",
        "maven_pom_not_valid",
    }:
        return (
            "maven_root_pom_scanprofile",
            "Build multi-module Maven projects from the aggregator POM",
        )
    if rule == "composer_private_package_repository_missing" or (
        eco == "packagist" and category == "ERROR_CATEGORY_PRIVATE_REGISTRY"
    ):
        return (
            "packagist_composer_pm",
            "Configure Composer Package Manager and private repositories",
        )
    if eco == "pypi" or rule in {
        "package_not_found_in_pypi",
        "setup_py_file_generic",
        "name_error",
        "attribute_error",
    }:
        if rule == "setup_py_file_generic":
            return ("python_setup_py_hygiene", "Migrate setup.py to a static manifest")
        if rule in {"name_error", "attribute_error"}:
            return ("python_scanprofile", "Pin Python and install build modules")
        return ("python_private_pypi", "Configure the private PyPI/Poetry index")
    if rule.startswith(("npm", "yarn", "pnpm")) or eco == "npm":
        if rule == "pnpm_workspace_packages_missing":
            return ("pnpm_workspace", "Fix pnpm-workspace.yaml package globs")
        if rule == "npm_git_dependency_error":
            return ("npm_git_creds", "Provide private git dependency credentials")
        return ("npm_registry", "Fix missing npm packages or private registry auth")
    if eco == "nuget" or "dotnet" in rule or "nuget" in rule:
        return ("nuget_dotnet", "Configure NuGet or exclude unsupported frameworks")
    if "gradle" in rule:
        return (
            "gradle_kotlin_scanprofile",
            "Apply Gradle/Kotlin Scan Profile settings",
        )
    if rule == "generic_registry_issue":
        return ("generic_private_registry", "Configure the ecosystem package manager")
    if rule == "no_best_match":
        return ("unmatched_inspect_logs", "Inspect scan logs and manifest/toolchain")
    return (f"other_{rule}", f"Remediate via platform guidance for rule `{rule}`")


def bu_label(child_namespace: str) -> str:
    """Humanize a first-level child namespace."""
    if child_namespace == "(root)":
        return "Tenant root"
    return child_namespace.replace("-", " ").replace("_", " ").title()


def safe_write(path: Path, text: str) -> None:
    """Write once, refusing latest pointers and existing files."""
    if "_latest" in path.name.lower():
        raise ValueError(f"Refusing to write latest pointer: {path}")
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing artifact: {path}")
    safe_write_text(path.parent, path, text)


def _fetch_child(
    tenant: str,
    child: str,
    timeout: float,
) -> dict[str, Any]:
    namespace = tenant if child == "(root)" else f"{tenant}.{child}"
    traverse = child != "(root)"
    client = Client(tenant=namespace, timeout=timeout)
    try:
        projects = []
        for value in client.Project.list(traverse=traverse, mask=PROJECT_MASK):
            row = _as_dict(value)
            row_ns = (row.get("tenant_meta") or {}).get("namespace") or namespace
            if child == "(root)" and row_ns != tenant:
                continue
            if child != "(root)" and _child_of(tenant, row_ns) != child:
                continue
            projects.append(
                {
                    "uuid": row.get("uuid"),
                    "name": (row.get("meta") or {}).get("name"),
                    "namespace": row_ns,
                }
            )
        all_pvs = client.PackageVersion.list(
            traverse=traverse,
            filter=MAIN,
            mask=PV_MASK,
        )
        failed_filter = (
            f"({MAIN}) and (spec.resolution_errors.unresolved exists or "
            "spec.resolution_errors.resolved exists)"
        )
        failed_pvs = client.PackageVersion.list(
            traverse=traverse,
            filter=failed_filter,
            mask=PV_ERROR_MASK,
        )
        return {
            "projects": projects,
            "all_pvs": [_as_dict(row) for row in all_pvs],
            "failed_pvs": [_as_dict(row) for row in failed_pvs],
        }
    finally:
        client.close()


def _theme_row(theme_id: str, value: dict[str, Any]) -> dict[str, Any]:
    return {
        "theme_id": theme_id,
        "action": value["action"],
        "projects": len(value["projects"]),
        "packages": value["packages"],
        "top_rules": [
            {"rule": rule, "packages": count}
            for rule, count in value["rules"].most_common(5)
        ],
        "ecosystems": dict(value["ecosystems"]),
    }


def _aggregate(
    tenant: str,
    slices: dict[str, dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    estate = {
        "projects_total": 0,
        "zero_packages": 0,
        "zero_pct": 0,
        "partial": 0,
        "full": 0,
        "packages_total": 0,
        "packages_resolved": 0,
        "packages_failed": 0,
    }
    per_namespace = []
    global_themes: dict[str, Any] = {}
    build = {
        "maven": {"packages": 0, "projects": set()},
        "gradle": {"packages": 0, "projects": set()},
        "rules": Counter(),
    }

    for child, child_slice in sorted(slices.items()):
        projects = child_slice["projects"]
        by_uuid = {row["uuid"]: row for row in projects if row.get("uuid")}
        totals: Counter[str] = Counter()
        failures: Counter[str] = Counter()
        details: dict[str, Any] = defaultdict(
            lambda: {
                "rules": Counter(),
                "themes": Counter(),
                "ecosystems": Counter(),
                "packages": [],
            }
        )
        local_themes: dict[str, Any] = {}
        for pv in child_slice["all_pvs"]:
            project_uuid = (pv.get("spec") or {}).get("project_uuid")
            if project_uuid in by_uuid:
                totals[project_uuid] += 1

        for pv in child_slice["failed_pvs"]:
            spec = pv.get("spec") or {}
            project_uuid = spec.get("project_uuid")
            if project_uuid not in by_uuid:
                continue
            errors = spec.get("resolution_errors") or {}
            item = errors.get("unresolved") or errors.get("resolved")
            if isinstance(item, list):
                item = item[0] if item else None
            best = _best_match(item)
            ecosystem = _ecosystem(pv, spec)
            theme_id, action = theme_bucket(
                best["matching_rule"], ecosystem, best["error_category"]
            )
            failures[project_uuid] += 1
            detail = details[project_uuid]
            detail["rules"][best["matching_rule"]] += 1
            detail["themes"][theme_id] += 1
            detail["ecosystems"][ecosystem] += 1
            detail["packages"].append(
                {
                    "pv_uuid": pv.get("uuid"),
                    "pv_name": (pv.get("meta") or {}).get("name"),
                    "ecosystem": ecosystem,
                    "matching_rule": best["matching_rule"],
                    "theme_id": theme_id,
                    "fixable": best["fixable"],
                    "fixable_notes": best["fixable_notes"],
                }
            )
            for themes in (local_themes, global_themes):
                theme = themes.setdefault(
                    theme_id,
                    {
                        "action": action,
                        "projects": set(),
                        "packages": 0,
                        "rules": Counter(),
                        "ecosystems": Counter(),
                        "by_child": defaultdict(
                            lambda: {"projects": set(), "packages": 0}
                        ),
                    },
                )
                theme["projects"].add(project_uuid)
                theme["packages"] += 1
                theme["rules"][best["matching_rule"]] += 1
                theme["ecosystems"][ecosystem] += 1
                if themes is global_themes:
                    theme["by_child"][child]["projects"].add(project_uuid)
                    theme["by_child"][child]["packages"] += 1
            if theme_id == "maven_private_artifactory":
                name = str((pv.get("meta") or {}).get("name") or "").lower()
                relative_path = str(spec.get("relative_path") or "").lower()
                is_gradle = "gradle" in name or "build.gradle" in relative_path
                key = "gradle" if is_gradle else "maven"
                build[key]["packages"] += 1
                build[key]["projects"].add(project_uuid)
                build["rules"][best["matching_rule"]] += 1

        zero_packages, zero_pct, partial, full = [], [], [], []
        package_total = package_resolved = package_failed = 0
        for project in projects:
            project_uuid = project["uuid"]
            total = int(totals.get(project_uuid, 0))
            failed = min(int(failures.get(project_uuid, 0)), total)
            resolved = total - failed
            row = {
                **project,
                "packages": total,
                "packages_resolved": resolved,
                "packages_failed": failed,
                "resolution_pct": round(100 * resolved / total, 1) if total else None,
            }
            if not total:
                zero_packages.append(row)
                continue
            package_total += total
            package_resolved += resolved
            package_failed += failed
            (zero_pct if not resolved else partial if failed else full).append(row)

        with_packages = len(projects) - len(zero_packages)
        local_theme_rows = [
            _theme_row(theme_id, value) for theme_id, value in local_themes.items()
        ]
        local_theme_rows.sort(
            key=lambda row: (-row["projects"], -row["packages"], row["theme_id"])
        )
        ns_row = {
            "child_namespace": child,
            "projects_total": len(projects),
            "projects_with_packages": with_packages,
            "zero_packages": len(zero_packages),
            "zero_pct_resolution": len(zero_pct),
            "partial_resolution": len(partial),
            "full_resolution": len(full),
            "packages_total": package_total,
            "packages_resolved": package_resolved,
            "packages_failed": package_failed,
            "coverage_pv_pct": (
                round(100 * package_resolved / package_total, 1)
                if package_total
                else None
            ),
            "coverage_fully_resolved_project_pct": (
                round(100 * len(full) / with_packages, 1) if with_packages else None
            ),
            "coverage_mean_project_pct": (
                round(
                    sum(row["resolution_pct"] for row in zero_pct + partial + full)
                    / with_packages,
                    1,
                )
                if with_packages
                else None
            ),
            "themes": local_theme_rows,
            "samples": {
                "zero_packages": [
                    {"name": row["name"], "namespace": row["namespace"]}
                    for row in zero_packages[:5]
                ],
                "zero_pct": [
                    {
                        "name": row["name"],
                        "packages": row["packages"],
                        "namespace": row["namespace"],
                    }
                    for row in sorted(zero_pct, key=lambda value: -value["packages"])[
                        :5
                    ]
                ],
                "partial": [
                    {
                        "name": row["name"],
                        "packages": row["packages"],
                        "resolved": row["packages_resolved"],
                        "failed": row["packages_failed"],
                        "resolution_pct": row["resolution_pct"],
                        "namespace": row["namespace"],
                    }
                    for row in sorted(
                        partial, key=lambda value: value["resolution_pct"]
                    )[:5]
                ],
            },
        }
        per_namespace.append(ns_row)
        estate["projects_total"] += len(projects)
        estate["zero_packages"] += len(zero_packages)
        estate["zero_pct"] += len(zero_pct)
        estate["partial"] += len(partial)
        estate["full"] += len(full)
        estate["packages_total"] += package_total
        estate["packages_resolved"] += package_resolved
        estate["packages_failed"] += package_failed

    projects_with_packages = estate["projects_total"] - estate["zero_packages"]
    estate.update(
        {
            "projects_with_packages": projects_with_packages,
            "coverage_pv_pct": (
                round(100 * estate["packages_resolved"] / estate["packages_total"], 1)
                if estate["packages_total"]
                else None
            ),
            "coverage_fully_resolved_project_pct": (
                round(100 * estate["full"] / projects_with_packages, 1)
                if projects_with_packages
                else None
            ),
        }
    )
    gap_projects = estate["zero_pct"] + estate["partial"]
    org_theme_rows = []
    for theme_id, value in global_themes.items():
        row = _theme_row(theme_id, value)
        row.update(
            {
                "pct_of_gap_projects": (
                    round(100 * row["projects"] / gap_projects, 1)
                    if gap_projects
                    else None
                ),
                "pct_of_failed_packages": (
                    round(100 * row["packages"] / estate["packages_failed"], 1)
                    if estate["packages_failed"]
                    else None
                ),
                "pct_of_projects_with_packages": (
                    round(100 * row["projects"] / projects_with_packages, 1)
                    if projects_with_packages
                    else None
                ),
                "by_child": {
                    child: {
                        "projects": len(child_value["projects"]),
                        "packages": child_value["packages"],
                    }
                    for child, child_value in sorted(
                        value["by_child"].items(),
                        key=lambda pair: -pair[1]["packages"],
                    )
                },
            }
        )
        if theme_id == "maven_private_artifactory":
            maven_packages = build["maven"]["packages"]
            gradle_packages = build["gradle"]["packages"]
            total_build_packages = maven_packages + gradle_packages
            row["build_system"] = {
                key: {
                    "packages": build[key]["packages"],
                    "projects": len(build[key]["projects"]),
                    "pct_packages": round(
                        100 * build[key]["packages"] / max(total_build_packages, 1),
                        1,
                    ),
                }
                for key in ("maven", "gradle")
            }
            row["build_system"]["note"] = (
                "All private-registry-theme PackageVersions use Maven signals."
                if not gradle_packages
                else "Private-registry theme includes Maven and Gradle signals."
            )
        org_theme_rows.append(row)
    org_theme_rows.sort(
        key=lambda row: (-row["packages"], -row["projects"], row["theme_id"])
    )
    theme_packages = build["maven"]["packages"] + build["gradle"]["packages"]
    theme_projects = build["maven"]["projects"] | build["gradle"]["projects"]
    build_system = {
        key: {
            "packages": build[key]["packages"],
            "projects": len(build[key]["projects"]),
            "pct_of_theme_packages": round(
                100 * build[key]["packages"] / max(theme_packages, 1), 1
            ),
        }
        for key in ("maven", "gradle")
    }
    build_system["maven"]["top_rules"] = dict(build["rules"].most_common(5))
    per_namespace.sort(key=lambda row: -row["projects_total"])
    return {
        "tenant": tenant,
        "generated_at": generated_at,
        "definitions": {
            "zero_packages": "Project has zero main-context PackageVersions",
            "zero_pct_resolution": (
                "Project has packages and every PackageVersion has dependency "
                "resolution errors"
            ),
            "partial_resolution": "Project has both resolved and failed packages",
            "full_resolution": "All PackageVersions have no dependency errors",
            "coverage_pv_pct": (
                "packages_resolved / packages_total among projects with at least "
                "one package"
            ),
            "coverage_fully_resolved_project_pct": (
                "full_resolution projects / projects_with_packages"
            ),
            "package_resolution": (
                "A PackageVersion fails when resolution_errors.unresolved or "
                "resolution_errors.resolved is present"
            ),
            "child_namespace": (
                "First path segment under the requested tenant; exact root projects "
                "are grouped as (root)"
            ),
        },
        "estate": estate,
        "by_child_namespace": per_namespace,
        "org_themes": {
            "gap_projects": gap_projects,
            "failed_packages": estate["packages_failed"],
            "projects_with_packages": projects_with_packages,
            "note": (
                "Project percentages may exceed 100% because a project can match "
                "multiple themes; each failed package maps to one theme."
            ),
            "themes": org_theme_rows,
        },
        "artifactory_theme_build_system": {
            "theme": "Private Maven registry / maven_private_artifactory",
            "definition": (
                "ecosystem=maven and matching rule is a private-artifact rule"
            ),
            "packages_total": theme_packages,
            "projects_total": len(theme_projects),
            "by_build_system": build_system,
        },
    }


def build_depr_coverage_report(
    tenant: str,
    *,
    timeout: float = 600.0,
    max_workers: int = 3,
) -> dict[str, Any]:
    """Build a coverage report by fanning out over first-level children."""
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")
    generated_at = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = Client(tenant=tenant, timeout=timeout)
    try:
        seed = root.Project.list(traverse=True, mask=PROJECT_MASK)
    finally:
        root.close()
    children = sorted(
        {
            _child_of(
                tenant,
                (_as_dict(project).get("tenant_meta") or {}).get("namespace"),
            )
            for project in seed
        }
    )
    slices: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_child, tenant, child, timeout): child
            for child in children
        }
        for future in as_completed(futures):
            slices[futures[future]] = future.result()
    return _aggregate(tenant, slices, generated_at)


def _render_technical_markdown(report: dict[str, Any]) -> str:
    estate = report["estate"]
    lines = [
        f"# Dependency Resolution Coverage Report — `{report['tenant']}`",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Estate summary",
        "",
        f"- Projects: **{estate['projects_total']}**",
        f"- Zero packages: **{estate['zero_packages']}**",
        f"- 0% DR: **{estate['zero_pct']}**",
        f"- Partial DR: **{estate['partial']}**",
        f"- Full DR: **{estate['full']}**",
        (
            f"- Package coverage: **{estate['coverage_pv_pct']}%** "
            f"({estate['packages_resolved']}/{estate['packages_total']})"
        ),
        (
            "- Fully-resolved project coverage: "
            f"**{estate['coverage_fully_resolved_project_pct']}%**"
        ),
        "",
        "## Counts per first-level child namespace",
        "",
        (
            "| Child namespace | Projects | 0 packages | 0% DR | Partial | Full | "
            "Resolved/total | Coverage |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["by_child_namespace"]:
        lines.append(
            f"| `{row['child_namespace']}` | {row['projects_total']} | "
            f"{row['zero_packages']} | {row['zero_pct_resolution']} | "
            f"{row['partial_resolution']} | {row['full_resolution']} | "
            f"{row['packages_resolved']}/{row['packages_total']} | "
            f"{row['coverage_pv_pct']}% |"
        )
    lines.extend(["", "## Remediation themes per namespace", ""])
    for row in report["by_child_namespace"]:
        if not row["themes"]:
            continue
        lines.extend(
            [
                f"### `{row['child_namespace']}`",
                "",
                "| Theme / fix | Projects | Packages | Top rules |",
                "|---|---:|---:|---|",
            ]
        )
        for theme in row["themes"]:
            rules = ", ".join(
                f"`{item['rule']}` ({item['packages']})"
                for item in theme["top_rules"][:3]
            )
            lines.append(
                f"| {theme['action']} | {theme['projects']} | "
                f"{theme['packages']} | {rules} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dependency-resolution coverage."
    )
    parser.add_argument("tenant", nargs="?", help="Tenant root namespace.")
    parser.add_argument("-n", "--namespace", help="Tenant root namespace.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_reports_subdir(RUN_BUCKET),
    )
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args(argv)
    if not args.namespace and not args.tenant:
        parser.error("provide tenant positionally or with -n/--namespace")
    if args.namespace and args.tenant and args.namespace != args.tenant:
        parser.error("positional tenant and --namespace must match")
    args.tenant = args.namespace or args.tenant
    return args


def main(argv: list[str] | None = None) -> int:
    from endorlabs.workflows.reports.export.html.depr_coverage import (
        render_exec_html,
        render_exec_markdown,
    )

    args = _parse_args(argv)
    report = build_depr_coverage_report(
        args.tenant,
        timeout=args.timeout,
        max_workers=args.workers,
    )
    output_dir = Path(args.output_dir)
    slug = sanitize_path_segment(args.tenant)
    timestamp = report["generated_at"]
    artifacts = {
        output_dir / f"{slug}__dr_coverage__{timestamp}.json": (
            json.dumps(report, indent=2) + "\n"
        ),
        output_dir / f"{slug}__dr_coverage__{timestamp}.md": (
            _render_technical_markdown(report)
        ),
        output_dir / f"{slug}__dr_coverage_EXEC__{timestamp}.md": (
            render_exec_markdown(report)
        ),
        output_dir / f"{slug}__dr_coverage_EXEC__{timestamp}.html": (
            render_exec_html(report)
        ),
    }
    for path, text in artifacts.items():
        safe_write(path, text)
        print(f"Wrote {path}", flush=True)
    print(json.dumps(report["estate"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
