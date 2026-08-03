"""Flatten ``endor.report_packet.v0`` cubes into CSV files under ``data/``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.tabular import TabularExport

_SEV = ("all", "critical", "high", "medium", "low")
_REACH = ("all", "reachable", "prf")


def _sca_report(cube: dict[str, Any]) -> dict[str, Any]:
    reports = cube.get("reports") or {}
    return reports.get("scaBurndown") or reports.get("findingsBurndown") or {}


def _gap_delta(cell: dict[str, Any]) -> int:
    return int(cell.get("gapEnd") or 0) - int(cell.get("gapStart") or 0)


def _gap_trend_label(delta: int) -> str:
    if delta > 0:
        return f"widening (+{delta})"
    if delta < 0:
        return f"narrowing ({delta})"
    return "stable (0)"


def _iter_matrix_cells(
    matrix: dict[str, Any] | None,
) -> list[tuple[str, str, dict[str, Any]]]:
    if not isinstance(matrix, dict):
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for sev in _SEV:
        reach_map = matrix.get(sev)
        if not isinstance(reach_map, dict):
            continue
        for reach in _REACH:
            cell = reach_map.get(reach)
            if isinstance(cell, dict) and "gapEnd" in cell:
                out.append((sev, reach, cell))
    return out


def onboarding_weekly_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = (cube.get("reports") or {}).get("onboarding") or {}
    by_week: dict[str, dict[str, Any]] = {}
    for row in report.get("weeklyAll") or []:
        w = str(row.get("w") or "")
        if not w:
            continue
        by_week[w] = {
            "week_start": w,
            "new_all": int(row.get("n") or 0),
            "cumulative_all": int(row.get("c") or 0),
            "new_distinct": 0,
            "cumulative_distinct": 0,
        }
    for row in report.get("weeklyDistinct") or []:
        w = str(row.get("w") or "")
        if not w:
            continue
        slot = by_week.setdefault(
            w,
            {
                "week_start": w,
                "new_all": 0,
                "cumulative_all": 0,
                "new_distinct": 0,
                "cumulative_distinct": 0,
            },
        )
        slot["new_distinct"] = int(row.get("n") or 0)
        slot["cumulative_distinct"] = int(row.get("c") or 0)
    return [by_week[k] for k in sorted(by_week)]


def onboarding_hierarchy_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = (cube.get("reports") or {}).get("onboarding") or {}
    by_ns: dict[str, dict[str, Any]] = {}
    for row in report.get("hierarchyAll") or []:
        ns = str(row.get("namespace") or "")
        if not ns:
            continue
        by_ns[ns] = {
            "namespace": ns,
            "count_all": int(row.get("count") or 0),
            "count_distinct": 0,
        }
    for row in report.get("hierarchyDistinct") or []:
        ns = str(row.get("namespace") or "")
        if not ns:
            continue
        slot = by_ns.setdefault(
            ns, {"namespace": ns, "count_all": 0, "count_distinct": 0}
        )
        slot["count_distinct"] = int(row.get("count") or 0)
    return [by_ns[k] for k in sorted(by_ns)]


def onboarding_cadence_weekly_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    cad = ((cube.get("reports") or {}).get("onboarding") or {}).get("cadence") or {}
    full = {
        str(r.get("w")): int(r.get("n") or 0) for r in (cad.get("weeklyMainFull") or [])
    }
    with_a = {
        str(r.get("w")): int(r.get("n") or 0)
        for r in (cad.get("weeklyMainWithAnalytics") or [])
    }
    ci = {str(r.get("w")): int(r.get("n") or 0) for r in (cad.get("weeklyCi") or [])}
    weeks = sorted(set(full) | set(with_a) | set(ci))
    return [
        {
            "week_start": w,
            "main_full_scans": full.get(w, 0),
            "main_with_analytics": with_a.get(w, 0),
            "ci_scans": ci.get(w, 0),
        }
        for w in weeks
        if w
    ]


def onboarding_cadence_by_tag_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    cad = ((cube.get("reports") or {}).get("onboarding") or {}).get("cadence") or {}
    rows = []
    for r in cad.get("byTag") or []:
        rows.append(
            {
                "tag": r.get("tag"),
                "project_count": int(r.get("projectCount") or 0),
                "main_full_scans": int(r.get("mainFullScans") or 0),
                "ci_scans": int(r.get("ciScans") or 0),
                "main_per_project": float(r.get("mainPerProject") or 0),
            }
        )
    rows.sort(key=lambda x: (-int(x["main_full_scans"]), str(x["tag"])))
    return rows


def onboarding_cadence_by_project_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = (cube.get("reports") or {}).get("onboarding") or {}
    cad = report.get("cadence") or {}
    by_p = cad.get("byProject") or {}
    projects = {
        str(p.get("uuid")): p for p in (report.get("projects") or []) if p.get("uuid")
    }
    rows = []
    for uid, cell in by_p.items():
        p = projects.get(str(uid)) or {}
        rows.append(
            {
                "uuid": uid,
                "name": p.get("name") or "",
                "namespace": p.get("namespace") or "",
                "main_full_scans": int(cell.get("mainFullScans") or 0),
                "ci_scans": int(cell.get("ciScans") or 0),
            }
        )
    rows.sort(key=lambda x: (-int(x["main_full_scans"]), str(x["name"])))
    return rows


def tag_catalog_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    meta = cube.get("tagSeriesMeta") or {}
    ready = set(meta.get("seriesReady") or [])
    pending = set(meta.get("seriesPending") or [])
    rows: list[dict[str, Any]] = []
    for entry in cube.get("tagCatalog") or []:
        tag = str(entry.get("tag") or "")
        if not tag:
            continue
        if tag in ready:
            status = "ready"
        elif tag in pending:
            status = "pending"
        else:
            status = "unknown"
        rows.append(
            {
                "tag": tag,
                "project_count": int(entry.get("projectCount") or 0),
                "series_status": status,
            }
        )
    rows.sort(key=lambda r: (-int(r["project_count"]), str(r["tag"])))
    return rows


def path_gap_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = _sca_report(cube)
    per_path = ((report.get("seriesFilters") or {}).get("perPath")) or {}
    rows: list[dict[str, Any]] = []
    for path, matrix in per_path.items():
        for sev, reach, cell in _iter_matrix_cells(matrix):
            delta = _gap_delta(cell)
            rows.append(
                {
                    "path": path,
                    "severity": sev,
                    "reachability": reach,
                    "gap_start": int(cell.get("gapStart") or 0),
                    "gap_end": int(cell.get("gapEnd") or 0),
                    "gap_delta": delta,
                    "gap_trend": _gap_trend_label(delta),
                }
            )
    rows.sort(
        key=lambda r: (str(r["path"]), str(r["severity"]), str(r["reachability"]))
    )
    return rows


def tag_gap_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = _sca_report(cube)
    per_tag = ((report.get("tagSeries") or {}).get("perTag")) or {}
    catalog = {
        str(e.get("tag") or ""): int(e.get("projectCount") or 0)
        for e in (cube.get("tagCatalog") or [])
        if e.get("tag")
    }
    rows: list[dict[str, Any]] = []
    for tag, path_map in per_tag.items():
        if not isinstance(path_map, dict):
            continue
        for path, matrix in path_map.items():
            for sev, reach, cell in _iter_matrix_cells(matrix):
                delta = _gap_delta(cell)
                rows.append(
                    {
                        "tag": tag,
                        "path": path,
                        "severity": sev,
                        "reachability": reach,
                        "project_count": catalog.get(str(tag), 0),
                        "gap_start": int(cell.get("gapStart") or 0),
                        "gap_end": int(cell.get("gapEnd") or 0),
                        "gap_delta": delta,
                        "gap_trend": _gap_trend_label(delta),
                    }
                )
    rows.sort(
        key=lambda r: (
            int(r["gap_delta"]),
            str(r["tag"]),
            str(r["path"]),
            str(r["severity"]),
            str(r["reachability"]),
        )
    )
    return rows


def _iter_code_matrix_cells(
    matrix: dict[str, Any] | None,
) -> list[tuple[str, str, dict[str, Any]]]:
    if not isinstance(matrix, dict):
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for sev, facet_map in matrix.items():
        if not isinstance(facet_map, dict):
            continue
        for facet, cell in facet_map.items():
            if isinstance(cell, dict) and "gapEnd" in cell:
                out.append((str(sev), str(facet), cell))
    return out


def code_path_gap_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = (cube.get("reports") or {}).get("codeFindingsBurndown") or {}
    by_cat = report.get("byCategory") or {}
    rows: list[dict[str, Any]] = []
    for category, block in by_cat.items():
        if not isinstance(block, dict):
            continue
        per_path = ((block.get("seriesFilters") or {}).get("perPath")) or {}
        for path, matrix in per_path.items():
            for sev, facet, cell in _iter_code_matrix_cells(matrix):
                delta = _gap_delta(cell)
                rows.append(
                    {
                        "category": category,
                        "path": path,
                        "severity": sev,
                        "facet": facet,
                        "gap_start": int(cell.get("gapStart") or 0),
                        "gap_end": int(cell.get("gapEnd") or 0),
                        "gap_delta": delta,
                        "gap_trend": _gap_trend_label(delta),
                    }
                )
    rows.sort(
        key=lambda r: (
            str(r["category"]),
            str(r["path"]),
            str(r["severity"]),
            str(r["facet"]),
        )
    )
    return rows


def code_tag_gap_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = (cube.get("reports") or {}).get("codeFindingsBurndown") or {}
    by_cat = report.get("byCategory") or {}
    catalog = {
        str(e.get("tag") or ""): int(e.get("projectCount") or 0)
        for e in (cube.get("tagCatalog") or [])
        if e.get("tag")
    }
    rows: list[dict[str, Any]] = []
    for category, block in by_cat.items():
        if not isinstance(block, dict):
            continue
        per_tag = ((block.get("tagSeries") or {}).get("perTag")) or {}
        for tag, path_map in per_tag.items():
            if not isinstance(path_map, dict):
                continue
            for path, matrix in path_map.items():
                for sev, facet, cell in _iter_code_matrix_cells(matrix):
                    delta = _gap_delta(cell)
                    rows.append(
                        {
                            "category": category,
                            "tag": tag,
                            "path": path,
                            "severity": sev,
                            "facet": facet,
                            "project_count": catalog.get(str(tag), 0),
                            "gap_start": int(cell.get("gapStart") or 0),
                            "gap_end": int(cell.get("gapEnd") or 0),
                            "gap_delta": delta,
                            "gap_trend": _gap_trend_label(delta),
                        }
                    )
    rows.sort(
        key=lambda r: (
            int(r["gap_delta"]),
            str(r["category"]),
            str(r["tag"]),
            str(r["path"]),
            str(r["severity"]),
            str(r["facet"]),
        )
    )
    return rows


def throughput_tag_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = _sca_report(cube)
    per_tag = ((report.get("throughput") or {}).get("perTag")) or {}
    rows: list[dict[str, Any]] = []
    for tag, scope in per_tag.items():
        if not isinstance(scope, dict):
            continue
        rows.append(
            {
                "tag": tag,
                "project_count": int(scope.get("projectCount") or 0),
                "main_scans_91d": int(scope.get("mainScans91d") or 0),
                "ci_run_scans_21d": int(scope.get("ciRunScans21d") or 0),
                "avg_main_scans_per_project": scope.get("avgMainScansPerProject"),
                "avg_main_per_week": scope.get("avgMainPerWeek"),
            }
        )
    rows.sort(key=lambda r: (-int(r["main_scans_91d"]), str(r["tag"])))
    return rows


def version_sprawl_top_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    report = (cube.get("reports") or {}).get("versionSprawl") or {}
    estate = report.get("estate") or {}
    if not isinstance(estate, dict):
        return []
    eco_map = estate.get("all") if isinstance(estate.get("all"), dict) else None
    if eco_map is None:
        return []
    # New: estate.all.all.all.t · mid: estate.all.all.t · legacy: estate.all.t
    cell: dict[str, Any] | None = None
    rel = eco_map.get("all")
    if isinstance(rel, dict) and isinstance(rel.get("all"), dict) and "t" in rel["all"]:
        cell = rel["all"]
    elif isinstance(rel, dict) and "t" in rel:
        cell = rel
    elif "t" in eco_map:
        cell = eco_map
    if not isinstance(cell, dict):
        return []
    rows: list[dict[str, Any]] = []
    for item in cell.get("t") or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        rows.append(
            {
                "package": str(item[0]),
                "version_count": int(item[1] or 0),
            }
        )
    rows.sort(key=lambda r: (-int(r["version_count"]), str(r["package"])))
    return rows


def _write_export(
    data_dir: Path,
    filename: str,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> Path:
    path = data_dir / filename
    TabularExport(rows=rows, columns=columns).write_csv(path, columns=columns)
    return path


def patches_family_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    patches = (cube.get("reports") or {}).get("patches") or {}
    rows: list[dict[str, Any]] = []
    for i, fam in enumerate(patches.get("families") or [], 1):
        rows.append(
            {
                "rank": i,
                "family": fam.get("family"),
                "available_findings": fam.get("findings"),
                "critical": fam.get("critical"),
                "high": fam.get("high"),
                "projects": fam.get("projects"),
                "versions": fam.get("versions"),
                "risk": fam.get("risk"),
            }
        )
    return rows


def patches_version_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    patches = (cube.get("reports") or {}).get("patches") or {}
    rows: list[dict[str, Any]] = []
    for fam in patches.get("families") or []:
        for vr in fam.get("version_rows") or []:
            rows.append(
                {
                    "family": fam.get("family"),
                    "version": vr.get("version"),
                    "available": vr.get("available"),
                    "to_request": vr.get("to_request"),
                    "critical": vr.get("critical"),
                    "high": vr.get("high"),
                    "projects": vr.get("projects"),
                    "risk": vr.get("risk"),
                    "risk_available": vr.get("risk_available"),
                    "reachable": vr.get("reachable"),
                    "unreachable": vr.get("unreachable"),
                }
            )
    return rows


def patches_unit_rows(cube: dict[str, Any]) -> list[dict[str, Any]]:
    patches = (cube.get("reports") or {}).get("patches") or {}
    rows: list[dict[str, Any]] = []
    for i, u in enumerate(patches.get("patch_units") or [], 1):
        rows.append(
            {
                "rank": i,
                "package_version": u.get("package_version"),
                "family": u.get("family"),
                "version": u.get("version"),
                "available": u.get("available"),
                "to_request": u.get("to_request"),
                "findings": u.get("findings"),
                "critical": u.get("critical"),
                "high": u.get("high"),
                "projects": u.get("projects"),
                "risk": u.get("risk"),
                "risk_available": u.get("risk_available"),
            }
        )
    return rows


def _packet_wide_exports(cube: dict[str, Any], out: Path) -> list[Path]:
    """CSV exports for the onboarding, sprawl, and burndown cube slices."""
    return [
        _write_export(
            out,
            "onboarding-weekly.csv",
            onboarding_weekly_rows(cube),
            [
                "week_start",
                "new_all",
                "cumulative_all",
                "new_distinct",
                "cumulative_distinct",
            ],
        ),
        _write_export(
            out,
            "onboarding-hierarchy.csv",
            onboarding_hierarchy_rows(cube),
            ["namespace", "count_all", "count_distinct"],
        ),
        _write_export(
            out,
            "onboarding-cadence-weekly.csv",
            onboarding_cadence_weekly_rows(cube),
            [
                "week_start",
                "main_full_scans",
                "main_with_analytics",
                "ci_scans",
            ],
        ),
        _write_export(
            out,
            "onboarding-cadence-by-tag.csv",
            onboarding_cadence_by_tag_rows(cube),
            [
                "tag",
                "project_count",
                "main_full_scans",
                "ci_scans",
                "main_per_project",
            ],
        ),
        _write_export(
            out,
            "onboarding-cadence-by-project.csv",
            onboarding_cadence_by_project_rows(cube),
            ["uuid", "name", "namespace", "main_full_scans", "ci_scans"],
        ),
        _write_export(
            out,
            "tag-catalog.csv",
            tag_catalog_rows(cube),
            ["tag", "project_count", "series_status"],
        ),
        _write_export(
            out,
            "path-gap-differentials.csv",
            path_gap_rows(cube),
            [
                "path",
                "severity",
                "reachability",
                "gap_start",
                "gap_end",
                "gap_delta",
                "gap_trend",
            ],
        ),
        _write_export(
            out,
            "tag-gap-differentials.csv",
            tag_gap_rows(cube),
            [
                "tag",
                "path",
                "severity",
                "reachability",
                "project_count",
                "gap_start",
                "gap_end",
                "gap_delta",
                "gap_trend",
            ],
        ),
        _write_export(
            out,
            "code-path-gap-differentials.csv",
            code_path_gap_rows(cube),
            [
                "category",
                "path",
                "severity",
                "facet",
                "gap_start",
                "gap_end",
                "gap_delta",
                "gap_trend",
            ],
        ),
        _write_export(
            out,
            "code-tag-gap-differentials.csv",
            code_tag_gap_rows(cube),
            [
                "category",
                "tag",
                "path",
                "severity",
                "facet",
                "project_count",
                "gap_start",
                "gap_end",
                "gap_delta",
                "gap_trend",
            ],
        ),
        _write_export(
            out,
            "throughput-by-tag.csv",
            throughput_tag_rows(cube),
            [
                "tag",
                "project_count",
                "main_scans_91d",
                "ci_run_scans_21d",
                "avg_main_scans_per_project",
                "avg_main_per_week",
            ],
        ),
        _write_export(
            out,
            "version-sprawl-top-packages.csv",
            version_sprawl_top_rows(cube),
            ["package", "version_count"],
        ),
    ]


def write_packet_raw_exports(
    cube: dict[str, Any],
    data_dir: str | Path,
    *,
    patches_only: bool = False,
) -> list[Path]:
    """Write spreadsheet-friendly CSV exports derived from *cube* under *data_dir*.

    With *patches_only*, skip the packet-wide exports whose cube slices were
    never collected — they would otherwise land as header-only CSVs.
    """
    out = Path(data_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = [] if patches_only else _packet_wide_exports(cube, out)
    written += [
        _write_export(
            out,
            "patches-top-families.csv",
            patches_family_rows(cube),
            [
                "rank",
                "family",
                "available_findings",
                "critical",
                "high",
                "projects",
                "versions",
                "risk",
            ],
        ),
        _write_export(
            out,
            "patches-versions.csv",
            patches_version_rows(cube),
            [
                "family",
                "version",
                "available",
                "to_request",
                "critical",
                "high",
                "projects",
                "risk",
                "risk_available",
                "reachable",
                "unreachable",
            ],
        ),
        _write_export(
            out,
            "patches-units-ranked.csv",
            patches_unit_rows(cube),
            [
                "rank",
                "package_version",
                "family",
                "version",
                "available",
                "to_request",
                "findings",
                "critical",
                "high",
                "projects",
                "risk",
                "risk_available",
            ],
        ),
    ]
    title = (
        "Endor Patches report — raw exports"
        if patches_only
        else "Executive report packet — raw exports"
    )
    manifest_lines = [
        title,
        "=" * len(title),
        "",
        "packet.cube.json                 Full interactive cube (source of truth)",
    ]
    if not patches_only:
        manifest_lines += [
            "onboarding-weekly.csv            Weekly registration counts",
            "onboarding-hierarchy.csv         Namespace hierarchy rollups",
            "onboarding-cadence-weekly.csv    MAIN full / with-analytics / CI weekly",
            "onboarding-cadence-by-tag.csv    Tag ranks by MAIN full + CI cadence",
            "onboarding-cadence-by-project.csv Project ranks by MAIN full + CI",
            "tag-catalog.csv                  Project.meta.tags catalog + series status",
            "path-gap-differentials.csv       SCA path × severity × reach gap deltas",
            "tag-gap-differentials.csv        SCA tag × path × severity × reach gap deltas",
            "code-path-gap-differentials.csv  Code findings path × category × facet gaps",
            "code-tag-gap-differentials.csv   Code findings tag × category × facet gaps",
            "throughput-by-tag.csv            Main/CI scan throughput by tag",
            "version-sprawl-top-packages.csv  Top packages by distinct version count",
        ]
    manifest_lines += [
        "patches-top-families.csv         Endor Patches top families by Available risk",
        "patches-versions.csv             Endor Patches family × version heat-map rows",
        "patches-units-ranked.csv         Endor Patches package@version units",
        "",
    ]
    manifest = out / "EXPORTS.txt"
    safe_write_text(out, manifest, "\n".join(manifest_lines))
    written.append(manifest)
    return written
