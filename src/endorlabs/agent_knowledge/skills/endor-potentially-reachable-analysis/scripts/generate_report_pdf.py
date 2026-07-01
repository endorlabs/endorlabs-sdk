#!/usr/bin/env python3
"""Generate dark-theme PDF for PRF approximation report from analysis JSON."""

from __future__ import annotations

import argparse
import html
import json
import math
import subprocess
import sys
from pathlib import Path

from paths import resolve_chrome

COLORS = {
    "NuGet": "#2E79B5",
    "NPM": "#1F8A65",
    "Maven": "#F0A040",
    "PyPI": "#7B64B8",
}


def esc(value: object) -> str:
    return html.escape(str(value))


def fmt_count(value: int) -> str:
    return f"{value:,}"


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def render_breakdown_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return (
            "<table><thead><tr>"
            "<th>Count</th><th>matching_rule</th><th>fixable</th>"
            "<th>explanation</th><th>fixable_notes</th>"
            "<th>PRF vulns</th><th>PRD vulns</th>"
            "<th>Precomputed reachability PVs</th>"
            "</tr></thead><tbody>"
            "<tr><td class='center' colspan='8'>No PVs in this category</td></tr>"
            "</tbody></table>"
        )
    body = []
    for idx, row in enumerate(rows):
        stripe = " class='striped'" if idx % 2 == 1 else ""
        body.append(
            "<tr"
            + stripe
            + "><td class='num'>"
            + esc(fmt_count(int(row["count"])))
            + "</td><td><code>"
            + esc(row["matching_rule"])
            + "</code></td><td class='center'>"
            + esc(row["fixable"] or "—")
            + "</td><td>"
            + esc(row["explanation"] or "—")
            + "</td><td>"
            + esc(row["fixable_notes"] or "—")
            + "</td><td class='num'>"
            + esc(fmt_count(int(row["prf_vulnerabilities"])))
            + "</td><td class='num'>"
            + esc(fmt_count(int(row["prd_vulnerabilities"])))
            + "</td><td class='num'>"
            + esc(fmt_count(int(row["precomputed_reachability_pvs"])))
            + "</td></tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Count</th><th>matching_rule</th><th>fixable</th>"
        "<th>explanation</th><th>fixable_notes</th>"
        "<th>PRF vulns</th><th>PRD vulns</th>"
        "<th>Precomputed reachability PVs</th>"
        "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"
    )


def render_pie_chart_svg(summary_rows: list[dict]) -> str:
    slices = [
        (row["ecosystem"], row["prfVulnerabilities"], COLORS[row["ecosystem"]])
        for row in summary_rows
        if not row.get("isTotal")
    ]
    total = sum(v for _, v, _ in slices)
    cx, cy, r = 120, 120, 96
    start = -90
    paths = []
    legend = []
    for label, value, color in slices:
        angle = 360 * value / total if total else 0
        end = start + angle
        large = 1 if angle > 180 else 0

        def polar(deg: float) -> tuple[float, float]:
            rad = math.radians(deg)
            return cx + r * math.cos(rad), cy + r * math.sin(rad)

        x1, y1 = polar(start)
        x2, y2 = polar(end)
        paths.append(
            f"<path d='M {cx} {cy} L {x1:.2f} {y1:.2f} A {r} {r} 0 {large} 1 {x2:.2f} {y2:.2f} Z' fill='{color}' />"
        )
        pct = 100 * value / total if total else 0
        legend.append(
            f"<div class='legend-item'><span class='swatch' style='background:{color}'></span>"
            f"<span>{esc(label)}</span><span class='legend-value'>{esc(fmt_count(value))} ({pct:.1f}%)</span></div>"
        )
        start = end

    return f"""
<div class="pie-block">
  <div class="pie-title">PRF vulnerabilities by ecosystem</div>
  <div class="pie-row">
    <svg width="240" height="240" viewBox="0 0 240 240" aria-label="PRF vulnerabilities by ecosystem">{"".join(paths)}</svg>
    <div class="legend">{"".join(legend)}</div>
  </div>
  <p class="caption">Main-context potentially reachable function vulnerabilities · n={esc(fmt_count(total))} across NuGet, NPM, Maven, PyPI</p>
</div>
"""


def render_html(data: dict) -> str:
    tenant = data["tenant"]
    summary_rows = data["summary_rows"]
    ecosystem_errors = data["ecosystem_errors"]
    missing = data.get("missing_parent_pvs", 0)
    total = next(r for r in summary_rows if r.get("isTotal"))

    summary_body = []
    for row in summary_rows:
        classes = ["total-row"] if row.get("isTotal") else []
        summary_body.append(
            f'<tr class="{" ".join(classes)}"><td>{esc(row["ecosystem"])}</td>'
            f"<td class='num'>{esc(fmt_count(row['prfVulnerabilities']))}</td>"
            f"<td class='num'>{esc(fmt_count(row['prdVulnerabilities']))}</td>"
            f"<td class='num'>{esc(fmt_count(row['approximatedVulns']))}</td>"
            f"<td class='num'>{esc(fmt_count(row['notApproximatedVulns']))}</td>"
            f"<td class='num'>{esc(fmt_pct(row['pctApproximatedVulns']))}</td>"
            f"<td class='num'>{esc(fmt_count(row['uniquePvs']))}</td>"
            f"<td class='num'>{esc(fmt_count(row['pvsWithDepResolutionErrors']))}</td>"
            f"<td class='num'>{esc(fmt_pct(row['pctPvsWithDepResolutionErrors']))}</td>"
            f"<td class='num'>{esc(fmt_count(row['pvsWithCallGraphErrors']))}</td>"
            f"<td class='num'>{esc(fmt_pct(row['pctPvsWithCallGraphErrors']))}</td></tr>"
        )

    ecosystem_sections = []
    for eco in ["NuGet", "NPM", "Maven", "PyPI"]:
        eco_data = ecosystem_errors[eco]
        ecosystem_sections.append(
            f"""
<section class="eco-section">
  <div class="section-header">
    <h2>{esc(eco)}</h2>
    <span class="badge">{esc(fmt_count(eco_data["dep_resolution_error_pvs"]))} dep · {esc(fmt_count(eco_data["call_graph_pvs"]))} call graph PVs</span>
  </div>
  <div class="subsection">
    <h3>Dependency resolution errors</h3>
    <p class="caption">Main-context PRF parent PackageVersions with spec.resolution_errors.unresolved or .resolved · n={esc(fmt_count(eco_data["dep_resolution_error_pvs"]))} PVs</p>
    {render_breakdown_table(eco_data["dep_resolution_breakdown"])}
  </div>
  <div class="subsection">
    <h3>Call graph errors</h3>
    <p class="caption">Main-context PRF parent PackageVersions with spec.resolution_errors.call_graph exists · n={esc(fmt_count(eco_data["call_graph_pvs"]))} PVs</p>
    {render_breakdown_table(eco_data["call_graph_breakdown"])}
  </div>
</section>
"""
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>PRF vulnerability &amp; PV resolution errors — main context</title>
<style>
  :root {{
    --bg-chrome: #141414;
    --bg-editor: #181818;
    --text-primary: #E4E4E4EB;
    --text-secondary: #E4E4E48D;
    --text-tertiary: #E4E4E45E;
    --stroke-primary: #E4E4E433;
    --stroke-secondary: #E4E4E41F;
    --fill-secondary: #E4E4E41E;
    --fill-tertiary: #E4E4E411;
    --accent: #599CE7;
    --warning: #E8C030E0;
    --info-bg: rgba(89, 156, 231, 0.12);
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg-chrome);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.45;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  .page {{ max-width: 1280px; margin: 0 auto; padding: 28px; }}
  h1 {{ font-size: 24px; line-height: 30px; font-weight: 590; margin: 0 0 6px; }}
  h2 {{ font-size: 18px; line-height: 24px; font-weight: 590; margin: 0; }}
  h3 {{ font-size: 16px; line-height: 22px; font-weight: 590; margin: 0 0 8px; }}
  .subtitle {{ color: var(--text-secondary); margin: 0; }}
  .caption {{ color: var(--text-tertiary); font-size: 12px; margin: 0 0 8px; }}
  .footnote {{ color: var(--text-secondary); font-size: 12px; margin-top: 8px; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 20px 0; }}
  .stat {{ background: var(--bg-editor); border: 1px solid var(--stroke-secondary); border-radius: 8px; padding: 14px 16px; }}
  .stat .label {{ color: var(--text-secondary); font-size: 12px; margin-bottom: 6px; }}
  .stat .value {{ font-size: 22px; font-weight: 590; line-height: 1.2; }}
  .stat.warning .value {{ color: var(--warning); }}
  .stat.info .value {{ color: var(--accent); }}
  .table-header-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .table-header-row .label {{ color: var(--text-secondary); font-size: 13px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; border: 1px solid var(--stroke-secondary); border-radius: 8px; overflow: hidden; font-size: 13px; background: var(--bg-editor); }}
  thead th {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--stroke-primary); color: var(--text-secondary); font-weight: 600; background: var(--fill-tertiary); }}
  tbody td {{ padding: 10px 12px; border-bottom: 1px solid var(--stroke-secondary); vertical-align: top; }}
  tbody tr.striped td {{ background: var(--fill-secondary); }}
  tbody tr.total-row td {{ background: var(--info-bg); }}
  td.num, th.num {{ text-align: right; }}
  td.center {{ text-align: center; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; color: var(--text-primary); }}
  .eco-section {{ border: 1px solid var(--stroke-secondary); border-radius: 8px; background: var(--bg-editor); padding: 16px; margin-bottom: 12px; page-break-inside: avoid; }}
  .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--stroke-secondary); }}
  .badge {{ color: var(--text-tertiary); font-size: 12px; }}
  .subsection {{ margin-bottom: 16px; }}
  .subsection:last-child {{ margin-bottom: 0; }}
  .section-title {{ color: var(--text-secondary); font-size: 13px; font-weight: 600; margin: 24px 0 12px; }}
  .pie-block {{ margin: 20px 0; page-break-inside: avoid; }}
  .pie-title {{ color: var(--text-secondary); font-size: 13px; font-weight: 600; margin-bottom: 12px; }}
  .pie-row {{ display: flex; align-items: center; gap: 28px; }}
  .legend {{ display: grid; gap: 10px; min-width: 260px; }}
  .legend-item {{ display: grid; grid-template-columns: 14px 80px 1fr; gap: 10px; align-items: center; font-size: 13px; }}
  .swatch {{ width: 12px; height: 12px; border-radius: 2px; display: inline-block; }}
  .legend-value {{ color: var(--text-tertiary); text-align: right; }}
  @page {{ margin: 16mm; size: A3 landscape; }}
</style>
</head>
<body>
<div class="page">
  <header>
    <h1>PRF vulnerability &amp; PV resolution errors — main context</h1>
    <p class="subtitle">{esc(tenant)} (incl. child namespaces)</p>
    <p class="caption">Source: Endor Labs Finding + PackageVersion APIs · CONTEXT_TYPE_MAIN · FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION · NuGet, NPM, Maven, PyPI</p>
  </header>

  {render_pie_chart_svg(summary_rows)}

  <div class="stats">
    <div class="stat"><div class="label">PRF vulnerabilities</div><div class="value">{esc(fmt_count(total["prfVulnerabilities"]))}</div></div>
    <div class="stat warning"><div class="label">Approximated vulns</div><div class="value">{esc(fmt_count(total["approximatedVulns"]))} ({esc(fmt_pct(total["pctApproximatedVulns"]))})</div></div>
    <div class="stat"><div class="label">Unique PVs</div><div class="value">{esc(fmt_count(total["uniquePvs"]))}</div></div>
    <div class="stat info"><div class="label">PVs with Dep Resolution errors</div><div class="value">{esc(fmt_count(total["pvsWithDepResolutionErrors"]))} ({esc(fmt_pct(total["pctPvsWithDepResolutionErrors"]))})</div></div>
  </div>

  <div class="table-header-row">
    <div class="label">Combined by ecosystem</div>
    <div class="caption" style="margin:0">Dep resolution errors = resolution_errors.unresolved or .resolved · Call graph errors = resolution_errors.call_graph exists · PRD vulnerabilities = PRF vulns also tagged FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Ecosystem</th>
        <th class="num">PRF vulnerabilities</th>
        <th class="num">PRD vulnerabilities</th>
        <th class="num">Approximated vulns</th>
        <th class="num">Not approximated vulns</th>
        <th class="num">% approximated vulns</th>
        <th class="num">Unique PVs</th>
        <th class="num">PVs with Dep Resolution errors</th>
        <th class="num">% PVs with Dep Resolution errors</th>
        <th class="num">PVs with Call Graph Errors</th>
        <th class="num">% PVs with Call Graph Errors</th>
      </tr>
    </thead>
    <tbody>
      {"".join(summary_body)}
    </tbody>
  </table>

  <p class="footnote">Total unique PVs ({esc(fmt_count(total["uniquePvs"]))}) is a union across ecosystems. Error breakdowns count main-context PackageVersions that are parents of PRF findings ({esc(missing)} parent UUIDs not found in main context are excluded). Call graph error analysis below covers PRF parent PVs with spec.resolution_errors.call_graph exists (same count as the summary table's PVs with Call Graph Errors).</p>

  <div class="section-title">Error analysis by ecosystem</div>
  {"".join(ecosystem_sections)}
</div>
</body>
</html>
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate HTML + PDF report from PRF analysis JSON."
    )
    parser.add_argument(
        "json_path", type=Path, help="Analysis JSON from run_analysis.py"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for HTML/PDF (default: same directory as JSON).",
    )
    parser.add_argument(
        "--chrome",
        type=Path,
        default=None,
        help="Chrome/Chromium binary (default: CHROME_PATH or common install paths).",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Write HTML only; skip PDF generation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    json_path = args.json_path
    if not json_path.is_file():
        print(f"JSON not found: {json_path}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or json_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    tenant = data["tenant"]
    html_path = output_dir / f"{tenant}-prf-approximation-main.html"
    pdf_path = output_dir / f"{tenant}-prf-approximation-main.pdf"

    html_content = render_html(data)
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Wrote {html_path}")

    if args.html_only:
        return 0

    chrome = resolve_chrome(args.chrome)
    if chrome is None:
        print(
            "Chrome/Chromium not found. Set CHROME_PATH or pass --chrome, "
            "or use --html-only.",
            file=sys.stderr,
        )
        return 1

    cmd = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        f"--print-to-pdf={pdf_path}",
        f"file://{html_path.resolve()}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    print(f"Wrote {pdf_path} ({pdf_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
