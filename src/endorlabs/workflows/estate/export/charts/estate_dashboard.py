"""Unified tabbed HTML dashboard for estate workspace analyses."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs.workflows.estate.export.charts.compile_graph_viz import (
    render_compile_graph_panels_html,
)
from endorlabs.workflows.estate.workspace.paths import ir_path, viz_path

ESTATE_DASHBOARD_SCHEMA = "endor.estate_dashboard.v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _risk_panel_from_document(document: dict[str, Any]) -> str:
    packages = document.get("packages") or []
    sections: list[str] = []
    for index, pkg in enumerate(packages, start=1):
        if not isinstance(pkg, dict):
            continue
        name = html.escape(str(pkg.get("package_name") or ""))
        risk_score = pkg.get("risk_score")
        critical = pkg.get("findings_critical")
        high = pkg.get("findings_high")
        cardinality = pkg.get("version_cardinality")
        versions = pkg.get("versions")
        if not isinstance(versions, list) or not versions:
            continue
        max_usage = max(
            int(row.get("usage_count") or 0)
            for row in versions
            if isinstance(row, dict)
        )
        if max_usage <= 0:
            max_usage = 1
        max_version_risk = max(
            (
                float(row.get("risk_score") or 0.0)
                for row in versions
                if isinstance(row, dict)
            ),
            default=0.0,
        )
        bars: list[str] = []
        for row in versions:
            if not isinstance(row, dict):
                continue
            version = html.escape(str(row.get("version") or ""))
            usage = int(row.get("usage_count") or 0)
            risk = float(row.get("risk_score") or 0.0)
            crit = int(row.get("findings_critical") or 0)
            hi = int(row.get("findings_high") or 0)
            width_pct = max(2.0, 100.0 * usage / max_usage)
            if row.get("risk_intensity") is not None:
                intensity = float(row.get("risk_intensity") or 0.0)
            elif max_version_risk > 0:
                intensity = risk / max_version_risk
            else:
                intensity = 0.0
            if risk <= 0 and crit == 0 and hi == 0:
                fill = "rgb(70,78,90)"
            else:
                red = min(255, int(120 + 135 * intensity))
                green = max(40, int(180 - 140 * intensity))
                blue = max(40, int(200 - 160 * intensity))
                fill = f"rgb({red},{green},{blue})"
            bars.append(
                f"""
                <div class="bar-row">
                  <div class="bar-label">{version}</div>
                  <div class="bar-track">
                    <div class="bar-fill" style="width:{width_pct:.1f}%;background:{fill}"></div>
                  </div>
                  <div class="bar-meta">{usage} rows · risk {risk:.0f} · C{crit}/H{hi}</div>
                </div>
                """
            )
        sections.append(
            f"""
            <section class="family">
              <header>
                <h2>#{index} {name}</h2>
                <p class="meta">risk {risk_score} · C{critical}/H{high} · {cardinality} versions</p>
              </header>
              {"".join(bars)}
            </section>
            """
        )
    if not sections:
        return '<section id="panel-risk" class="panel active"><p class="hint">No risk packages in IR.</p></section>'
    return (
        f'<section id="panel-risk" class="panel active">{"".join(sections)}</section>'
    )


def render_estate_dashboard_html(
    workspace_root: Path,
    *,
    namespace_label: str | None = None,
    collapse_prefixes: tuple[str, ...] = (),
) -> str:
    ns_label = html.escape(namespace_label or workspace_root.name)
    risk_path = ir_path(workspace_root, "risk_cardinality.json")
    risk_panel = ""
    if risk_path.is_file():
        risk_doc = json.loads(risk_path.read_text(encoding="utf-8"))
        risk_panel = _risk_panel_from_document(risk_doc)
    else:
        risk_panel = '<section id="panel-risk" class="panel active"><p class="hint">Run analyze risk step first.</p></section>'

    graph_dashboard = ""
    graph_bipartite = ""
    try:
        graph_dashboard, graph_bipartite = render_compile_graph_panels_html(
            workspace_root, collapse_prefixes=collapse_prefixes
        )
        graph_dashboard = graph_dashboard.replace(
            'id="panel-dashboard"', 'id="panel-graph"', 1
        )
        graph_dashboard = graph_dashboard.replace(
            'class="panel active"', 'class="panel"', 1
        )
        graph_bipartite = graph_bipartite.replace(
            'id="panel-bipartite"', 'id="panel-bipartite"', 1
        )
    except FileNotFoundError:
        graph_dashboard = '<section id="panel-graph" class="panel"><p class="hint">Run analyze graph step first.</p></section>'
        graph_bipartite = '<section id="panel-bipartite" class="panel"><p class="hint">Graph bipartite unavailable.</p></section>'

    generated = html.escape(_utc_now())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Estate dashboard — {ns_label}</title>
  <style>
    :root {{
      --bg: #0f1419; --panel: #161d27; --text: #e7ecf1; --muted: #8a9bab;
      --accent: #4f8cff; --con: #56b6c2; --pub: #f0a020; --border: #2a3441;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 12px 16px; border-bottom: 1px solid var(--border); }}
    h1 {{ margin: 0 0 4px; font-size: 1rem; }}
    .sub {{ color: var(--muted); font-size: 0.8rem; margin: 0; }}
    nav {{ display: flex; gap: 8px; padding: 10px 16px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }}
    nav button {{
      background: var(--panel); border: 1px solid var(--border); color: var(--text);
      padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.85rem;
    }}
    nav button.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    main {{ padding: 16px; max-width: 960px; margin: 0 auto; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }}
    .stat {{ background: var(--panel); padding: 12px; border-radius: 8px; border: 1px solid var(--border); }}
    .stat b {{ display: block; font-size: 1.25rem; }}
    .stat span {{ font-size: 0.72rem; color: var(--muted); }}
    .columns-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    @media (max-width: 700px) {{ .columns-2 {{ grid-template-columns: 1fr; }} }}
    h3 {{ font-size: 0.85rem; color: var(--muted); margin: 0 0 10px; }}
    .family {{ margin-bottom: 28px; }}
    .family header h2 {{ margin: 0 0 4px; font-size: 0.95rem; }}
    .meta {{ color: var(--muted); font-size: 0.75rem; margin: 0 0 12px; }}
    #panel-risk .bar-row {{ display: grid; grid-template-columns: 140px 1fr 160px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 0.75rem; }}
    .graph-bar-row {{ display: grid; grid-template-columns: 140px 1fr 36px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 0.75rem; }}
    .bar-track {{ background: #1a222d; height: 8px; border-radius: 4px; overflow: hidden; display: block; }}
    .bar-fill {{ display: block; height: 100%; min-width: 2px; }}
    .bar-fill.pub {{ background: var(--pub); }}
    .bar-fill.con {{ background: var(--con); }}
    .bar-meta, .bar-val {{ color: var(--muted); font-size: 0.68rem; }}
    .bar-val {{ text-align: right; }}
    .tiles {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
    .tile {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; text-align: center; }}
    .tile strong {{ display: block; font-size: 1.1rem; }}
    .tile span {{ font-size: 0.7rem; color: var(--muted); }}
    table.data {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; margin-bottom: 16px; }}
    table.data th, table.data td {{ border: 1px solid var(--border); padding: 6px 8px; text-align: left; }}
    table.data th {{ background: var(--panel); color: var(--muted); }}
    .bipartite {{ width: 100%; max-width: 900px; background: var(--panel); border-radius: 8px; border: 1px solid var(--border); }}
    .svg-title {{ fill: var(--muted); font-size: 11px; }}
    .node-label {{ fill: var(--text); font-size: 10px; }}
    .deg-label {{ fill: var(--muted); font-size: 9px; text-anchor: end; }}
    .dot.con {{ fill: var(--con); }}
    .dot.pub {{ fill: var(--pub); }}
    .hint {{ color: var(--muted); font-size: 0.78rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Estate dashboard ({ns_label})</h1>
    <p class="sub">{ESTATE_DASHBOARD_SCHEMA} · generated {generated}</p>
  </header>
  <nav>
    <button type="button" class="tab active" data-tab="risk">Risk families</button>
    <button type="button" class="tab" data-tab="graph">Internal dependencies</button>
    <button type="button" class="tab" data-tab="bipartite">Top importers and producers</button>
  </nav>
  <main>
    {risk_panel}
    {graph_dashboard}
    {graph_bipartite}
  </main>
  <script>
    document.querySelectorAll(".tab").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("panel-" + btn.dataset.tab).classList.add("active");
      }});
    }});
  </script>
</body>
</html>
"""


def export_estate_dashboard(
    workspace_root: Path,
    *,
    namespace_label: str | None = None,
    top_n: int = 20,
    scorer_name: str = "critical_high_count",
    collapse_prefixes: tuple[str, ...] = (),
) -> Path:
    """Write unified dashboard HTML to ``viz/estate_dashboard.html``."""
    del top_n, scorer_name  # consumed during analyze; kept for CLI symmetry
    out = viz_path(workspace_root, "estate_dashboard.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    html_doc = render_estate_dashboard_html(
        workspace_root,
        namespace_label=namespace_label,
        collapse_prefixes=collapse_prefixes,
    )
    out.write_text(html_doc, encoding="utf-8")
    return out
