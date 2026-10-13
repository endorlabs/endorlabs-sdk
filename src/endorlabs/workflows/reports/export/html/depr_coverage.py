"""Markdown and HTML exports for dependency-resolution coverage reports."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import Any

EXEC_THEME_COPY = {
    "maven_private_artifactory": (
        "Private Maven registry (Artifactory / Nexus) — Maven only",
        "Connect the private Maven registry so internal parent POMs and artifacts resolve.",
    ),
    "maven_root_pom_scanprofile": (
        "Multi-module Maven scan configuration",
        "Standardize Scan Profiles so multi-module Java apps build from the root POM.",
    ),
    "packagist_composer_pm": (
        "Private Composer / Packagist",
        "Configure Composer Package Manager for private PHP packages.",
    ),
    "npm_registry": (
        "Private npm registry / missing packages",
        "Configure npm credentials or remediate missing package references.",
    ),
    "nuget_dotnet": (
        ".NET / NuGet configuration",
        "Configure NuGet and/or exclude unsupported legacy frameworks.",
    ),
    "python_private_pypi": (
        "Private PyPI / Poetry registry",
        "Configure PyPI Package Manager and private Poetry indexes.",
    ),
    "python_setup_py_hygiene": (
        "Python setup.py modernization",
        "Move dynamic setup.py packages to static manifests.",
    ),
    "unmatched_inspect_logs": (
        "Needs investigation",
        "Review unclassified scan logs and assign a remediation path.",
    ),
    "gradle_kotlin_scanprofile": (
        "Gradle / Kotlin scan configuration",
        "Apply Gradle/Kotlin Scan Profile settings.",
    ),
    "npm_git_creds": (
        "Private git npm dependencies",
        "Provide credentials for private git-based npm packages.",
    ),
    "pnpm_workspace": (
        "pnpm workspace configuration",
        "Fix pnpm-workspace.yaml package globs.",
    ),
    "python_scanprofile": (
        "Python toolchain Scan Profile",
        "Pin Python and required build modules in the Scan Profile.",
    ),
}


def _display_tenant(tenant: str) -> str:
    return tenant.replace("-", " ").replace("_", " ").title()


def _bu_label(child_namespace: str) -> str:
    if child_namespace == "(root)":
        return "Tenant root"
    return child_namespace.replace("-", " ").replace("_", " ").title()


def _date(timestamp: str, *, long: bool = False) -> str:
    try:
        parsed = datetime.strptime(timestamp[:8], "%Y%m%d").replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return timestamp
    if long:
        return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
    return f"{parsed.day} {parsed.strftime('%b')} {parsed.year}"


def _pct(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.1f}%"


def _delta(value: float, suffix: str = "") -> str:
    sign = "+" if value >= 0 else "−"
    return f"{sign}{abs(value):,.1f}{suffix}"


def _int_delta(value: int) -> str:
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return f"{sign}{abs(value):,}"


def _theme(report: dict[str, Any], theme_id: str) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in (report.get("org_themes") or {}).get("themes", [])
            if row.get("theme_id") == theme_id
        ),
        None,
    )


def render_exec_markdown(report: dict) -> str:
    """Render the daily executive dependency-resolution report."""
    tenant = str(report["tenant"])
    display = _display_tenant(tenant)
    estate = report["estate"]
    themes = (report.get("org_themes") or {}).get("themes", [])
    artifactory = _theme(report, "maven_private_artifactory")
    lines = [
        f"# {display} — Dependency Resolution Coverage",
        "",
        f"**As of:** {_date(str(report['generated_at']), long=True)}  ",
        f"**Scope:** Endor Labs tenant `{tenant}` (all first-level namespaces)",
        "",
        "## Executive summary",
        "",
        (
            f"Across **{estate['projects_with_packages']:,}** repositories with packages, "
            f"Endor Labs resolves **{_pct(estate['coverage_pv_pct'])}** of package "
            f"inventories (**{estate['packages_resolved']:,}** of "
            f"**{estate['packages_total']:,}** packages). "
            f"**{_pct(estate['coverage_fully_resolved_project_pct'])}** of scanned "
            "repositories have fully healthy dependency resolution."
        ),
        "",
        "### Recommended focus",
        "",
    ]
    recommendations = []
    for theme in themes[:3]:
        title, action = EXEC_THEME_COPY.get(
            theme["theme_id"], (theme["action"], theme["action"])
        )
        recommendations.append(
            f"{len(recommendations) + 1}. **{title}** — {action} "
            f"({theme['projects']:,} repositories / {theme['packages']:,} packages)."
        )
    lines.extend(recommendations or ["No dependency-resolution failure themes remain."])
    lines.extend(
        [
            "",
            "## Coverage by business unit",
            "",
            (
                "| Business unit | Repos | Scanned | Coverage | Fully healthy | "
                "0% resolution | Partial |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report["by_child_namespace"]:
        lines.append(
            f"| {_bu_label(row['child_namespace'])} | {row['projects_total']} | "
            f"{row['projects_with_packages']} | {_pct(row['coverage_pv_pct'])} | "
            f"{row['full_resolution']} | {row['zero_pct_resolution']} | "
            f"{row['partial_resolution']} |"
        )
    lines.extend(
        [
            "",
            "Coverage = resolved packages ÷ all packages among repositories with packages.",
            "",
            "## Organization failure themes",
            "",
        ]
    )
    if artifactory:
        build = report.get("artifactory_theme_build_system", {}).get(
            "by_build_system", {}
        )
        maven = build.get("maven", {})
        gradle = build.get("gradle", {})
        lines.extend(
            [
                (
                    f"**Private-registry build split:** Maven "
                    f"**{maven.get('projects', 0):,}** repositories / "
                    f"**{maven.get('packages', 0):,}** packages; Gradle "
                    f"**{gradle.get('projects', 0):,}** / "
                    f"**{gradle.get('packages', 0):,}**."
                ),
                "",
            ]
        )
    lines.extend(
        [
            "| Theme | Repos | Packages | Failed-package share | Action |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for theme in themes:
        title, action = EXEC_THEME_COPY.get(
            theme["theme_id"], (theme["action"], theme["action"])
        )
        lines.append(
            f"| {title} | {theme['projects']} | {theme['packages']} | "
            f"{_pct(theme.get('pct_of_failed_packages'))} | {action} |"
        )
    lines.extend(
        [
            "",
            "## What good looks like",
            "",
            "- Empty repositories remain outside the package-coverage denominator.",
            "- Prioritize the largest failure theme, then standardize Scan Profiles.",
            "- Track package coverage and fully healthy repository rate by business unit.",
            "",
            f"_Generated: {report['generated_at']} UTC (dated artifact only)_",
            "",
        ]
    )
    return "\n".join(lines)


def _style() -> str:
    return """
:root{--bg:#f7f6f3;--surface:#fff;--ink:#1a1a1a;--muted:#5c5c5c;
--line:#e2e0da;--accent:#0f6e56;--soft:#e6f4ef;--info:#1f4e79}
*{box-sizing:border-box}body{margin:0;font-family:"IBM Plex Sans","Segoe UI",
system-ui,sans-serif;color:var(--ink);background:var(--bg);line-height:1.5}
.wrap{max-width:1100px;margin:auto;padding:40px 24px 64px}h1{font-size:28px;
margin:0 0 8px}h2{margin:34px 0 10px;font-size:20px}.lede,.muted{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}
.card,.panel{background:var(--surface);border:1px solid var(--line);border-radius:10px;
padding:16px}.label{font-size:12px;color:var(--muted)}.value{font-size:28px;
font-weight:650;color:var(--accent)}.chart{height:320px;position:relative}
table{width:100%;border-collapse:collapse;background:var(--surface);font-size:13px}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left}
th{background:#f0eee8;color:var(--muted)}.num{text-align:right;
font-variant-numeric:tabular-nums}.callout{padding:16px 18px;background:var(--soft);
border:1px solid #b7d9cb;border-radius:10px;margin:20px 0}
footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);
color:var(--muted);font-size:12px}@media(max-width:800px){.cards{grid-template-columns:repeat(2,1fr)}}
@media(max-width:500px){.cards{grid-template-columns:1fr}}"""


def render_exec_html(report: dict) -> str:
    """Render polished daily HTML with BU and failure-theme charts."""
    estate = report["estate"]
    display = _display_tenant(str(report["tenant"]))
    namespaces = report["by_child_namespace"]
    themes = (report.get("org_themes") or {}).get("themes", [])[:8]
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(_bu_label(row['child_namespace']))}</td>"
        f"<td class='num'>{row['projects_with_packages']:,}</td>"
        f"<td class='num'>{_pct(row['coverage_pv_pct'])}</td>"
        f"<td class='num'>{row['full_resolution']:,}</td>"
        f"<td class='num'>{row['packages_failed']:,}</td></tr>"
        for row in namespaces
    )
    labels = [_bu_label(row["child_namespace"]) for row in namespaces]
    coverage = [row["coverage_pv_pct"] for row in namespaces]
    theme_labels = [
        EXEC_THEME_COPY.get(row["theme_id"], (row["theme_id"], ""))[0] for row in themes
    ]
    theme_packages = [row["packages"] for row in themes]
    chart_data = json.dumps(
        {
            "buLabels": labels,
            "coverage": coverage,
            "themeLabels": theme_labels,
            "themePackages": theme_packages,
        }
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1"><title>{html.escape(display)} —
Dependency Resolution Coverage</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
<style>{_style()}</style></head><body><main class="wrap">
<header><h1>{html.escape(display)} — Dependency Resolution Coverage</h1>
<p class="lede">As of {_date(str(report["generated_at"]), long=True)} · all first-level namespaces</p></header>
<div class="callout"><strong>{_pct(estate["coverage_pv_pct"])}</strong> package
coverage across <strong>{estate["packages_total"]:,}</strong> packages.</div>
<section class="cards">
<div class="card"><div class="label">Package coverage</div><div class="value">{_pct(estate["coverage_pv_pct"])}</div></div>
<div class="card"><div class="label">Fully healthy rate</div><div class="value">{_pct(estate["coverage_fully_resolved_project_pct"])}</div></div>
<div class="card"><div class="label">Packages resolved</div><div class="value">{estate["packages_resolved"]:,}</div></div>
<div class="card"><div class="label">Fully healthy repos</div><div class="value">{estate["full"]:,}</div></div>
</section>
<h2>Business-unit coverage</h2><div class="panel"><div class="chart"><canvas id="bu"></canvas></div></div>
<table><thead><tr><th>Business unit</th><th class="num">Scanned</th>
<th class="num">Coverage</th><th class="num">Fully healthy</th>
<th class="num">Failed packages</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Failure-theme packages</h2><div class="panel"><div class="chart"><canvas id="themes"></canvas></div></div>
<footer>Generated {html.escape(str(report["generated_at"]))} UTC · dated artifact only</footer>
</main><script>const d={chart_data};
Chart.defaults.color="#5c5c5c";
new Chart(document.getElementById("bu"),{{type:"bar",data:{{labels:d.buLabels,
datasets:[{{label:"Package coverage (%)",data:d.coverage,backgroundColor:"#0f6e56"}}]}},
options:{{responsive:true,maintainAspectRatio:false,scales:{{y:{{beginAtZero:true,max:100,
ticks:{{callback:v=>v+"%"}}}}}},plugins:{{legend:{{display:false}}}}}}}});
new Chart(document.getElementById("themes"),{{type:"doughnut",data:{{
labels:d.themeLabels,datasets:[{{data:d.themePackages,backgroundColor:
["#0f6e56","#1f4e79","#8a5a00","#8b2e2e","#6b6b6b","#4d8c78","#7089a0","#b08a49"]}}]}},
options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:"bottom"}}}}}}}});
</script></body></html>"""


def _progress_rows(checkpoints: list[dict]) -> list[dict[str, Any]]:
    children = {
        row["child_namespace"]
        for report in checkpoints
        for row in report.get("by_child_namespace", [])
    }
    rows = []
    for child in children:
        values = []
        for report in checkpoints:
            match = next(
                (
                    row
                    for row in report.get("by_child_namespace", [])
                    if row["child_namespace"] == child
                ),
                {},
            )
            values.append(match)
        first, last = values[0], values[-1]
        first_coverage = first.get("coverage_pv_pct")
        last_coverage = last.get("coverage_pv_pct")
        delta = (
            float(last_coverage) - float(first_coverage)
            if first_coverage is not None and last_coverage is not None
            else 0.0
        )
        rows.append(
            {
                "child": child,
                "label": _bu_label(child),
                "values": values,
                "delta": delta,
                "packages_delta": int(last.get("packages_resolved", 0))
                - int(first.get("packages_resolved", 0)),
                "healthy_delta": int(last.get("full_resolution", 0))
                - int(first.get("full_resolution", 0)),
            }
        )
    return sorted(rows, key=lambda row: (-row["delta"], row["label"]))


def render_progress_markdown(
    checkpoints: list[dict],
    *,
    as_of: str | None = None,
) -> str:
    """Render executive progress Markdown from two or more checkpoints."""
    if len(checkpoints) < 2:
        raise ValueError("progress reporting requires at least two checkpoints")
    checkpoints = sorted(checkpoints, key=lambda item: str(item["generated_at"]))
    last = checkpoints[-1]
    display = _display_tenant(str(last["tenant"]))
    dates = [_date(str(report["generated_at"])) for report in checkpoints]
    estates = [report["estate"] for report in checkpoints]
    coverage_delta = float(estates[-1]["coverage_pv_pct"]) - float(
        estates[0]["coverage_pv_pct"]
    )
    healthy_delta = float(estates[-1]["coverage_fully_resolved_project_pct"]) - float(
        estates[0]["coverage_fully_resolved_project_pct"]
    )
    packages_delta = int(estates[-1]["packages_resolved"]) - int(
        estates[0]["packages_resolved"]
    )
    full_delta = int(estates[-1]["full"]) - int(estates[0]["full"])
    as_of_label = as_of or _date(str(last["generated_at"]), long=True)
    lines = [
        f"# {display} — Dependency Resolution Progress",
        "",
        f"**As of:** {as_of_label}  ",
        f"**Period:** {' → '.join(dates)}",
        "",
        "## Executive summary",
        "",
        (
            f"Package-level dependency resolution coverage moved from "
            f"**{_pct(estates[0]['coverage_pv_pct'])}** to "
            f"**{_pct(estates[-1]['coverage_pv_pct'])}** "
            f"(**{_delta(coverage_delta, ' percentage points')}**). Fully healthy "
            f"scanned repositories moved from "
            f"**{_pct(estates[0]['coverage_fully_resolved_project_pct'])}** to "
            f"**{_pct(estates[-1]['coverage_fully_resolved_project_pct'])}**."
        ),
        "",
        "| Outcome | " + " | ".join(dates) + " | Change |",
        "|---|" + "---:|" * len(dates) + "---:|",
        "| Package coverage | "
        + " | ".join(_pct(item["coverage_pv_pct"]) for item in estates)
        + f" | **{_delta(coverage_delta, ' pp')}** |",
        "| Fully healthy rate | "
        + " | ".join(
            _pct(item["coverage_fully_resolved_project_pct"]) for item in estates
        )
        + f" | **{_delta(healthy_delta, ' pp')}** |",
        "| Packages resolved | "
        + " | ".join(f"{item['packages_resolved']:,}" for item in estates)
        + f" | **{_int_delta(packages_delta)}** |",
        "| Fully healthy repos | "
        + " | ".join(f"{item['full']:,}" for item in estates)
        + f" | **{_int_delta(full_delta)}** |",
        "",
        "## Artifactory theme movement",
        "",
    ]
    art = [_theme(report, "maven_private_artifactory") or {} for report in checkpoints]
    lines.append(
        "Private Maven registry theme: repositories **"
        + " → ".join(f"{item.get('projects', 0):,}" for item in art)
        + "**; packages **"
        + " → ".join(f"{item.get('packages', 0):,}" for item in art)
        + "**."
    )
    progress_rows = _progress_rows(checkpoints)
    lines.extend(
        [
            "",
            "## Coverage by business unit",
            "",
            "| Business unit | "
            + " | ".join(dates)
            + " | Change | Packages resolved Δ | Fully healthy Δ |",
            "|---|" + "---:|" * len(dates) + "---:|---:|---:|",
        ]
    )
    for row in progress_rows:
        lines.append(
            f"| {row['label']} | "
            + " | ".join(_pct(value.get("coverage_pv_pct")) for value in row["values"])
            + f" | **{_delta(row['delta'], ' pp')}** | "
            f"{_int_delta(row['packages_delta'])} | "
            f"{_int_delta(row['healthy_delta'])} |"
        )
    standouts = [row for row in progress_rows if row["delta"] > 0][:4]
    lines.extend(["", "### Standouts", ""])
    if standouts:
        for index, row in enumerate(standouts, 1):
            first_pct = row["values"][0].get("coverage_pv_pct")
            last_pct = row["values"][-1].get("coverage_pv_pct")
            lines.append(
                f"{index}. **{row['label']}** — {_pct(first_pct)} → "
                f"{_pct(last_pct)} ({_delta(row['delta'], ' pp')}); "
                f"{_int_delta(row['packages_delta'])} packages resolved."
            )
    else:
        lines.append("No business unit recorded a positive coverage change.")
    art_project_delta = int(art[-1].get("projects", 0)) - int(art[0].get("projects", 0))
    lines.extend(
        [
            "",
            "## Value delivered",
            "",
            f"- **{_int_delta(packages_delta)} packages** are now resolved.",
            f"- **{_int_delta(full_delta)} repositories** moved into fully healthy resolution.",
            (
                f"- **{_int_delta(art_project_delta)} private-registry-theme "
                "repositories** remain compared with the first checkpoint."
            ),
            "",
            "## Still the priority",
            "",
        ]
    )
    if art[-1]:
        lines.append(
            f"1. **Private Maven registry** — {art[-1].get('projects', 0):,} "
            f"repositories / {art[-1].get('packages', 0):,} packages remain."
        )
    lines.append(
        "2. **Multi-module Java Scan Profiles** — standardize root-POM builds."
    )
    lagging = sorted(
        progress_rows,
        key=lambda row: row["values"][-1].get("coverage_pv_pct") or 0,
    )[:2]
    if lagging:
        lines.append(
            "3. **Targeted business-unit follow-through** — focus on "
            + " and ".join(row["label"] for row in lagging)
            + "."
        )
    lines.extend(
        [
            "",
            f"_Generated from checkpoints {', '.join(str(item['generated_at']) for item in checkpoints)}_",
            "",
        ]
    )
    return "\n".join(lines)


def render_progress_html(checkpoints: list[dict]) -> str:
    """Render progress HTML with trajectory, grouped BU, and gain charts."""
    if len(checkpoints) < 2:
        raise ValueError("progress reporting requires at least two checkpoints")
    checkpoints = sorted(checkpoints, key=lambda item: str(item["generated_at"]))
    estates = [report["estate"] for report in checkpoints]
    dates = [_date(str(report["generated_at"])) for report in checkpoints]
    rows = _progress_rows(checkpoints)
    first, last = estates[0], estates[-1]
    coverage_delta = float(last["coverage_pv_pct"]) - float(first["coverage_pv_pct"])
    healthy_delta = float(last["coverage_fully_resolved_project_pct"]) - float(
        first["coverage_fully_resolved_project_pct"]
    )
    packages_delta = int(last["packages_resolved"]) - int(first["packages_resolved"])
    full_delta = int(last["full"]) - int(first["full"])
    table_rows = "".join(
        "<tr>"
        f"<td>{html.escape(row['label'])}</td>"
        + "".join(
            f"<td class='num'>{_pct(value.get('coverage_pv_pct'))}</td>"
            for value in row["values"]
        )
        + f"<td class='num'>{_delta(row['delta'], ' pp')}</td>"
        f"<td class='num'>{_int_delta(row['packages_delta'])}</td>"
        f"<td class='num'>{_int_delta(row['healthy_delta'])}</td></tr>"
        for row in rows
    )
    art = [_theme(report, "maven_private_artifactory") or {} for report in checkpoints]
    chart_data = json.dumps(
        {
            "dates": dates,
            "coverage": [item["coverage_pv_pct"] for item in estates],
            "healthy": [
                item["coverage_fully_resolved_project_pct"] for item in estates
            ],
            "labels": [row["label"] for row in rows],
            "buSeries": [
                [row["values"][index].get("coverage_pv_pct") for row in rows]
                for index in range(len(checkpoints))
            ],
            "gains": [row["delta"] for row in rows],
            "artifactory": [item.get("packages", 0) for item in art],
        }
    ).replace("</", "<\\/")
    display = _display_tenant(str(checkpoints[-1]["tenant"]))
    headers = "".join(f"<th class='num'>{html.escape(date)}</th>" for date in dates)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(display)} — Dependency Resolution Progress</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
<style>{_style()}</style></head><body><main class="wrap">
<h1>{html.escape(display)} — Dependency Resolution Progress</h1>
<p class="lede">As of {_date(str(checkpoints[-1]["generated_at"]), long=True)} ·
{" → ".join(html.escape(date) for date in dates)}</p>
<div class="callout">Package coverage changed <strong>{_delta(coverage_delta, " pp")}</strong>
to <strong>{_pct(last["coverage_pv_pct"])}</strong>, with
<strong>{_int_delta(packages_delta)} resolved packages</strong>.</div>
<section class="cards">
<div class="card"><div class="label">Package coverage</div><div class="value">{_pct(last["coverage_pv_pct"])}</div><div>{_delta(coverage_delta, " pp")}</div></div>
<div class="card"><div class="label">Fully healthy rate</div><div class="value">{_pct(last["coverage_fully_resolved_project_pct"])}</div><div>{_delta(healthy_delta, " pp")}</div></div>
<div class="card"><div class="label">Packages resolved</div><div class="value">{last["packages_resolved"]:,}</div><div>{_int_delta(packages_delta)}</div></div>
<div class="card"><div class="label">Fully healthy repos</div><div class="value">{last["full"]:,}</div><div>{_int_delta(full_delta)}</div></div>
</section>
<h2>Coverage trajectory</h2><div class="panel"><div class="chart"><canvas id="trajectory"></canvas></div></div>
<h2>Artifactory-theme movement</h2><div class="panel"><div class="chart"><canvas id="artifactory"></canvas></div></div>
<h2>Business-unit coverage</h2><div class="panel"><div class="chart"><canvas id="business"></canvas></div></div>
<div class="panel"><div class="chart"><canvas id="gains"></canvas></div></div>
<table><thead><tr><th>Business unit</th>{headers}<th class="num">Change</th>
<th class="num">Packages resolved Δ</th><th class="num">Fully healthy Δ</th>
</tr></thead><tbody>{table_rows}</tbody></table>
<h2>Value delivered</h2><ul><li>{_int_delta(packages_delta)} packages resolved</li>
<li>{_int_delta(full_delta)} fully healthy repositories</li></ul>
<div class="callout"><strong>Still the priority:</strong> private Maven registry
connectivity, multi-module Java Scan Profiles, and targeted work in the lowest-coverage
business units.</div>
<footer>Generated from {len(checkpoints)} dated checkpoints · no latest pointer written</footer>
</main><script>const d={chart_data};const colors=["#6b6b6b","#1f4e79","#0f6e56","#8a5a00"];
new Chart(document.getElementById("trajectory"),{{type:"line",data:{{labels:d.dates,
datasets:[{{label:"Package coverage",data:d.coverage,borderColor:"#0f6e56"}},
{{label:"Fully healthy rate",data:d.healthy,borderColor:"#1f4e79"}}]}},
options:{{responsive:true,maintainAspectRatio:false,scales:{{y:{{max:100,ticks:{{callback:v=>v+"%"}}}}}}}}}});
new Chart(document.getElementById("artifactory"),{{type:"line",data:{{labels:d.dates,
datasets:[{{label:"Artifactory-theme packages",data:d.artifactory,borderColor:"#8b2e2e"}}]}},
options:{{responsive:true,maintainAspectRatio:false}}}});
new Chart(document.getElementById("business"),{{type:"bar",data:{{labels:d.labels,
datasets:d.dates.map((date,i)=>({{label:date,data:d.buSeries[i],backgroundColor:colors[i%colors.length]}}))}},
options:{{responsive:true,maintainAspectRatio:false,scales:{{y:{{max:100,ticks:{{callback:v=>v+"%"}}}}}}}}}});
new Chart(document.getElementById("gains"),{{type:"bar",data:{{labels:d.labels,
datasets:[{{label:"Coverage gain (pp)",data:d.gains,backgroundColor:"#0f6e56"}}]}},
options:{{indexAxis:"y",responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}}}}}});
</script></body></html>"""
