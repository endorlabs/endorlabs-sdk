"""Render executive report packet HTML from a cube dict."""

from __future__ import annotations

import json
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Any

from endorlabs.context.paths import sanitize_path_segment
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.reports.export.csv.packet_exports import (
    write_packet_raw_exports,
)
from endorlabs.workflows.reports.schemas.packet_v0 import (
    REPORT_PACKET_SCHEMA,
    RUN_BUCKET,
)

from . import copy as copy_mod

_SHELL_ASSETS = (
    "endor-logo.png",
    "endor-wordmark.png",
    "chart.umd.min.js",
)


def _tokens_css() -> str:
    root = resources.files("endorlabs.workflows.reports.export.html.shell")
    return (root / "tokens.css").read_text(encoding="utf-8")


@contextmanager
def _shell_asset_path(name: str) -> Generator[Path]:
    root = resources.files("endorlabs.workflows.reports.export.html.shell")
    with resources.as_file(root / "assets" / name) as path:
        yield Path(path)


def _copy_shell_assets(out: Path) -> list[Path]:
    assets_dir = out / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in _SHELL_ASSETS:
        dest = assets_dir / name
        with _shell_asset_path(name) as src:
            shutil.copyfile(src, dest)
        written.append(dest)
    return written


def _chart_helpers_js() -> str:
    return """function brandVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
function chartTheme() {
  const muted = brandVar("--endor-muted");
  const grid = brandVar("--endor-border");
  return {
    muted,
    grid,
    accent: brandVar("--endor-accent"),
    ok: brandVar("--endor-ok"),
    warn: brandVar("--endor-warn"),
    danger: brandVar("--endor-danger"),
    neutral: brandVar("--endor-chart-neutral"),
    secondary: brandVar("--endor-chart-secondary"),
  };
}
function chartScales(theme) {
  return {
    x: { ticks: { color: theme.muted }, grid: { color: theme.grid } },
    y: { ticks: { color: theme.muted }, grid: { color: theme.grid } },
  };
}
const SEV_OPTIONS = [
  {v:"critical", l:"Critical and higher"},
  {v:"high_plus", l:"High and higher"},
  {v:"medium_plus", l:"Medium and higher"},
  {v:"all", l:"All severities"},
];
const SEV_LABELS = Object.fromEntries(SEV_OPTIONS.map(o => [o.v, o.l]));
const SEV_THRESHOLD_BANDS = {
  critical: ["critical"],
  high_plus: ["critical", "high"],
  medium_plus: ["critical", "high", "medium"],
  all: ["all"],
};
function sumSeriesCells(parts) {
  if (!parts.length) return null;
  const cats = parts[0].categories || [];
  const n = cats.length;
  const weeklyNew = Array(n).fill(0);
  const weeklyResolved = Array(n).fill(0);
  for (const p of parts) {
    const wn = p.weeklyNew || [];
    const wr = p.weeklyResolved || [];
    for (let i = 0; i < n; i++) {
      weeklyNew[i] += Number(wn[i]) || 0;
      weeklyResolved[i] += Number(wr[i]) || 0;
    }
  }
  const cumulativeNew = [];
  const cumulativeResolved = [];
  const gaps = [];
  let cn = 0, cr = 0;
  for (let i = 0; i < n; i++) {
    cn += weeklyNew[i];
    cr += weeklyResolved[i];
    cumulativeNew.push(cn);
    cumulativeResolved.push(cr);
    gaps.push(cn - cr);
  }
  const gapStart = gaps.length ? gaps[0] : 0;
  const gapEnd = gaps.length ? gaps[gaps.length - 1] : 0;
  let gapTrend = "stable";
  if (gapEnd > gapStart) gapTrend = "widening";
  else if (gapEnd < gapStart) gapTrend = "narrowing";
  return {
    categories: cats,
    weeklyNew,
    weeklyResolved,
    cumulativeNew,
    cumulativeResolved,
    gaps,
    gapStart,
    gapEnd,
    gapTrend,
    periodCaption: parts[0].periodCaption || "",
  };
}
function resolveSevCell(matrix, sevKey, facet) {
  if (!matrix) return null;
  const bands = SEV_THRESHOLD_BANDS[sevKey];
  if (!bands) {
    const cell = matrix[sevKey]?.[facet];
    return cell || null;
  }
  if (bands.length === 1 && bands[0] === "all") {
    return matrix.all?.[facet] ?? null;
  }
  if (bands.length === 1) {
    return matrix[bands[0]]?.[facet] ?? null;
  }
  const parts = bands.map(b => matrix[b]?.[facet]).filter(Boolean);
  return sumSeriesCells(parts);
}
"""


def _nav(active: str) -> str:
    def cls(key: str) -> str:
        return ' class="active"' if key == active else ""

    return f"""<div class="nav">
  <a{cls("on")} href="01-onboarding.html">Onboarding</a>
  <a{cls("vs")} href="02-version-sprawl.html">Version sprawl</a>
  <a{cls("sca")} href="03-sca-burndown.html">SCA burndown</a>
  <a{cls("sast")} href="04-sast-burndown.html">SAST burndown</a>
</div>"""


def _sca_burndown_report(cube: dict[str, Any]) -> dict[str, Any]:
    reports = cube.get("reports") or {}
    return reports.get("scaBurndown") or reports.get("findingsBurndown") or {}


def _header(
    *,
    title: str,
    purpose: str,
    tenant: str,
    pulled_at: str,
) -> str:
    pulled = (pulled_at or "")[:10]
    return f"""<header class="site-header">
  <img class="brand-wordmark" src="assets/endor-wordmark.png" alt="Endor Labs"/>
  <span class="brand-tag">Executive report</span>
</header>
<h1>{title}</h1>
<p class="purpose">{purpose}</p>
<p class="meta">Namespace <strong>{tenant}</strong> · Data as of {pulled} · Schema {REPORT_PACKET_SCHEMA}</p>
"""


def _footer() -> str:
    return f"""<footer class="site-footer">
  <img class="footer-mark" src="assets/endor-logo.png" alt="" width="28" height="28"/>
  <p class="footer-copy">Generated by the Endor Labs SDK · not the live product UI · {REPORT_PACKET_SCHEMA}</p>
</footer>"""


def _page(body: str, *, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<script src="assets/chart.umd.min.js"></script>
<style>{_tokens_css()}</style>
</head>
<body>
<div class="wrap">
{body}
{_footer()}
</div>
</body>
</html>
"""


def _render_onboarding(cube: dict[str, Any]) -> str:
    tenant = cube.get("tenant") or ""
    pulled = cube.get("pulledAt") or ""
    report = (cube.get("reports") or {}).get("onboarding") or {}
    slim = {
        **report,
        "tagCatalog": [
            {"tag": t["tag"], "projectCount": t["projectCount"]}
            for t in (cube.get("tagCatalog") or [])
            if t.get("tag")
        ],
    }
    payload = json.dumps(slim, separators=(",", ":"))
    return _page(
        f"""{_nav("on")}
{_header(title=copy_mod.H1_ONBOARDING, purpose=copy_mod.PURPOSE_ONBOARDING, tenant=tenant, pulled_at=pulled)}
{copy_mod.GLOSSARY_HTML}
<div class="card">
  <div class="card-h">Filters</div>
  <div class="filters">
    <label class="field">Project tag<select id="tag"></select></label>
  </div>
  <div class="toggles">
    <label class="toggle"><input type="checkbox" id="once"/> Count each repository only once (earliest registration wins)</label>
    <label class="toggle"><input type="checkbox" id="analytics"/> Include analytics ScanResults in MAIN weekly series</label>
    <span class="pill" id="modePill"></span>
  </div>
</div>
<div class="stats" id="stats"></div>
<div class="card">
  <div class="card-h">Onboarding progress · cumulative</div>
  <p class="caption">Cumulative project registrations by ISO week (Monday UTC). Source: Project.meta.create_time. Tag filter scopes this series.</p>
  <div class="chart-box"><canvas id="cumChart"></canvas></div>
</div>
<div class="card">
  <div class="card-h">Scan &amp; PR cadence · weekly</div>
  <p class="caption" id="cadenceCaption">Organization-wide ScanResult counts (~90d). Default MAIN = TYPE_ALL_SCANS only; CI = CONTEXT_TYPE_CI_RUN.</p>
  <div class="chart-box sm"><canvas id="weekChart"></canvas></div>
</div>
<div class="grid-2" id="leaders"></div>
<h2>Inclusive namespace hierarchy</h2>
<p class="caption">Each path includes projects in that namespace and its children (tag filter applied).</p>
<table class="data" id="hierTable"><thead><tr><th>Namespace</th><th class="num">Count</th></tr></thead><tbody></tbody></table>
<script>
{_chart_helpers_js()}
const R = {payload};
let cumChart, weekChart;
function fillSelect(el, options) {{
  el.innerHTML = options.map(o => `<option value="${{o.v}}">${{o.l}}</option>`).join("");
}}
function weekMonday(iso) {{
  const d = new Date(iso + (iso.endsWith("Z") ? "" : "T00:00:00Z"));
  if (Number.isNaN(d.getTime())) return "";
  const day = d.getUTCDay();
  const diff = (day + 6) % 7; // Monday=0
  d.setUTCDate(d.getUTCDate() - diff);
  return d.toISOString().slice(0, 10);
}}
function filteredProjects() {{
  const tag = document.getElementById("tag").value;
  const all = R.projects || [];
  if (!tag || tag === "all") return all;
  const uuids = new Set((R.cadence?.tagProjectUuids || {{}})[tag] || []);
  if (uuids.size) return all.filter(p => uuids.has(p.uuid));
  return all.filter(p => (p.tags || []).includes(tag));
}}
function weeklyFromProjects(projects, once) {{
  const byName = new Map();
  const dated = [];
  for (const p of projects) {{
    const ct = p.create_time;
    if (!ct) continue;
    const w = weekMonday(String(ct).slice(0, 10));
    if (!w) continue;
    dated.push({{ w, name: p.name || p.uuid, t: ct }});
  }}
  dated.sort((a, b) => String(a.t).localeCompare(String(b.t)));
  let items = dated;
  if (once) {{
    for (const row of dated) {{
      if (!byName.has(row.name)) byName.set(row.name, row);
    }}
    items = [...byName.values()].sort((a, b) => String(a.t).localeCompare(String(b.t)));
  }}
  const buckets = new Map();
  for (const row of items) buckets.set(row.w, (buckets.get(row.w) || 0) + 1);
  const weeks = [...buckets.keys()].sort();
  let c = 0;
  return weeks.map(w => {{ const n = buckets.get(w) || 0; c += n; return {{ w, n, c }}; }});
}}
function hierarchyFromProjects(projects) {{
  const totals = new Map();
  for (const p of projects) {{
    const ns = p.namespace || "";
    if (!ns) continue;
    const parts = ns.split(".");
    for (let i = 1; i <= parts.length; i++) {{
      const key = parts.slice(0, i).join(".");
      totals.set(key, (totals.get(key) || 0) + 1);
    }}
  }}
  return [...totals.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([namespace, count]) => ({{ namespace, count }}));
}}
function alignWeekly(series) {{
  const map = new Map((series || []).map(r => [r.w, r.n || 0]));
  return map;
}}
function unionWeeks(...maps) {{
  const s = new Set();
  for (const m of maps) for (const k of m.keys()) s.add(k);
  return [...s].sort();
}}
function leaderTable(rows, cols, selectedTag) {{
  if (!rows.length) return `<p class="muted">No cadence rows for this filter.</p>`;
  const head = cols.map(c => `<th class="${{c.num ? "num" : ""}}">${{c.l}}</th>`).join("");
  const body = rows.map(r => {{
    const sel = r.tag && r.tag === selectedTag ? " selected" : "";
    const click = r.tag ? ` class="clickable${{sel}}" data-tag="${{r.tag}}"` : "";
    const cells = cols.map(c => {{
      const v = r[c.k];
      const text = c.num ? Number(v || 0).toLocaleString() : (v || "");
      return `<td class="${{c.num ? "num" : ""}}">${{text}}</td>`;
    }}).join("");
    return `<tr${{click}}>${{cells}}</tr>`;
  }}).join("");
  return `<table class="data"><thead><tr>${{head}}</tr></thead><tbody>${{body}}</tbody></table>`;
}}
function renderLeaders(tag) {{
  const cad = R.cadence || {{}};
  let tagRows = [...(cad.topTags || cad.byTag || [])];
  let projRows = [...(cad.topProjects || [])];
  if (tag && tag !== "all") {{
    const uuids = new Set((cad.tagProjectUuids || {{}})[tag] || []);
    const byP = cad.byProject || {{}};
    const projects = R.projects || [];
    const byUuid = Object.fromEntries(projects.map(p => [p.uuid, p]));
    projRows = [...uuids].map(uid => {{
      const cell = byP[uid] || {{}};
      const p = byUuid[uid] || {{}};
      return {{
        uuid: uid,
        name: p.name || uid,
        namespace: p.namespace || "",
        mainFullScans: cell.mainFullScans || 0,
        ciScans: cell.ciScans || 0,
      }};
    }}).sort((a, b) => (b.mainFullScans - a.mainFullScans) || (b.ciScans - a.ciScans));
    tagRows = (cad.byTag || []).filter(t => t.tag === tag);
  }}
  const tagHtml = leaderTable(tagRows.slice(0, 25), [
    {{k:"tag", l:"Tag"}}, {{k:"projectCount", l:"Projects", num:true}},
    {{k:"mainFullScans", l:"MAIN full", num:true}}, {{k:"ciScans", l:"CI/PR", num:true}},
    {{k:"mainPerProject", l:"MAIN / project", num:true}},
  ], tag);
  const projHtml = leaderTable(projRows.slice(0, 25), [
    {{k:"name", l:"Project"}}, {{k:"namespace", l:"Namespace"}},
    {{k:"mainFullScans", l:"MAIN full", num:true}}, {{k:"ciScans", l:"CI/PR", num:true}},
  ], tag);
  document.getElementById("leaders").innerHTML = `
    <div class="card"><div class="card-h">Tags by scan cadence</div>
      <p class="caption">Ranked by MAIN TYPE_ALL_SCANS then CI (~90d). Click a tag to filter.</p>
      ${{tagHtml}}</div>
    <div class="card"><div class="card-h">Projects by scan cadence</div>
      <p class="caption">Top projects by MAIN full scans then CI (~90d).</p>
      ${{projHtml}}</div>`;
  document.getElementById("leaders").querySelectorAll("tr.clickable[data-tag]").forEach(tr => {{
    tr.addEventListener("click", () => {{
      const t = tr.getAttribute("data-tag");
      const sel = document.getElementById("tag");
      if (t && sel) {{ sel.value = t; render(); }}
    }});
  }});
}}
function render() {{
  const theme = chartTheme();
  const once = document.getElementById("once").checked;
  const analytics = document.getElementById("analytics").checked;
  const tag = document.getElementById("tag").value;
  document.getElementById("modePill").textContent = [
    once ? "Distinct repositories" : "All registrations",
    analytics ? "MAIN includes analytics" : "MAIN full scans only",
    tag !== "all" ? ("tag:" + tag) : "all tags",
  ].join(" · ");
  document.getElementById("modePill").className = "pill info";
  const projects = filteredProjects();
  const weeklyReg = weeklyFromProjects(projects, once);
  const cad = R.cadence || {{}};
  const totals = cad.totals || {{}};
  const lookback = cad.lookbackDays || 91;
  document.getElementById("stats").innerHTML = `
    <div class="stat"><b>${{projects.length.toLocaleString()}}</b><span>${{once ? "Distinct repos (filter)" : "Projects (filter)"}}</span></div>
    <div class="stat info"><b>${{(totals.mainFullScans||0).toLocaleString()}}</b><span>MAIN full scans (${{lookback}}d, org)</span></div>
    <div class="stat"><b>${{(totals.ciScans||0).toLocaleString()}}</b><span>CI / PR scans (${{lookback}}d, org)</span></div>
    <div class="stat warn"><b>${{(totals.distinctPrContextIds||0).toLocaleString()}}</b><span>Distinct PR contexts</span></div>`;
  const mainMap = alignWeekly(analytics ? cad.weeklyMainWithAnalytics : cad.weeklyMainFull);
  const ciMap = alignWeekly(cad.weeklyCi);
  const weeks = unionWeeks(mainMap, ciMap);
  const weekLabels = weeks.map(w => String(w).slice(5));
  const opts = {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ labels: {{ color: theme.muted }} }} }},
    scales: chartScales(theme)
  }};
  if (cumChart) cumChart.destroy();
  if (weekChart) weekChart.destroy();
  const regLabels = weeklyReg.map(r => String(r.w||"").slice(5));
  cumChart = new Chart(document.getElementById("cumChart"), {{
    type: "line",
    data: {{
      labels: regLabels,
      datasets: [
        {{ label: once ? "Distinct repositories" : "All registrations",
           data: weeklyReg.map(r => r.c), borderColor: theme.accent, tension: 0.15 }},
      ]
    }},
    options: opts
  }});
  weekChart = new Chart(document.getElementById("weekChart"), {{
    type: "bar",
    data: {{
      labels: weekLabels,
      datasets: [
        {{ label: analytics ? "MAIN (incl. analytics)" : "MAIN full scans",
           data: weeks.map(w => mainMap.get(w) || 0), backgroundColor: theme.accent + "99" }},
        {{ label: "CI / PR scans",
           data: weeks.map(w => ciMap.get(w) || 0), backgroundColor: theme.warn + "99" }},
      ]
    }},
    options: opts
  }});
  document.getElementById("cadenceCaption").textContent =
    `Organization-wide ScanResult counts (~${{lookback}}d). ` +
    (analytics
      ? "MAIN includes TYPE_ANALYTICS / TYPE_ANALYTICS_CHECK."
      : "MAIN = TYPE_ALL_SCANS only (analytics excluded).") +
    " CI = CONTEXT_TYPE_CI_RUN.";
  const hier = hierarchyFromProjects(
    once
      ? (() => {{
          const seen = new Map();
          for (const p of projects) {{
            const n = p.name || p.uuid;
            if (!seen.has(n)) seen.set(n, p);
          }}
          return [...seen.values()];
        }})()
      : projects
  );
  document.querySelector("#hierTable tbody").innerHTML = hier.map(h =>
    `<tr><td>${{h.namespace}}</td><td class="num">${{h.count.toLocaleString()}}</td></tr>`
  ).join("");
  renderLeaders(tag);
}}
fillSelect(document.getElementById("tag"), [
  {{v:"all", l:"All project tags"}},
  ...(R.tagCatalog||[]).map(t => ({{v:t.tag, l: `${{t.tag}} (${{t.projectCount}} projects)`}}))
]);
["tag","once","analytics"].forEach(id => document.getElementById(id).addEventListener("change", render));
render();
</script>
""",
        title=f"{copy_mod.H1_ONBOARDING} — {tenant}",
    )


def _render_version_sprawl(cube: dict[str, Any]) -> str:
    tenant = cube.get("tenant") or ""
    pulled = cube.get("pulledAt") or ""
    report = (cube.get("reports") or {}).get("versionSprawl") or {}
    slim = {
        "tenant": tenant,
        "pulledAt": pulled,
        "histKeys": report.get("histKeys") or [],
        "ecosystems": report.get("ecosystems") or [],
        "relations": report.get("relations") or ["all", "direct", "transitive"],
        "visibilities": report.get("visibilities") or ["all", "public", "private"],
        "pathOptions": cube.get("pathOptions") or ["all"],
        "tags": [
            {"tag": t["tag"], "projectCount": t["projectCount"]}
            for t in (cube.get("tagCatalog") or [])
        ],
        "estate": report.get("estate") or {},
        "perPath": report.get("perPath") or {},
        "perTag": report.get("perTag") or {},
    }
    payload = json.dumps(slim, separators=(",", ":"))
    return _page(
        f"""{_nav("vs")}
{_header(title=copy_mod.H1_VERSION_SPRAWL, purpose=copy_mod.PURPOSE_VERSION_SPRAWL, tenant=tenant, pulled_at=pulled)}
{copy_mod.GLOSSARY_HTML}
<div class="card">
  <div class="card-h">Filters</div>
  <div class="filters">
    <label class="field">Namespace<select id="ns"></select></label>
    <label class="field">Project tag<select id="tag"></select></label>
    <label class="field">Ecosystem<select id="eco"></select></label>
  </div>
  <div class="toggles">
    <label class="toggle"><input type="checkbox" id="direct"/> Direct only</label>
    <label class="toggle"><input type="checkbox" id="transitive"/> Transitive only</label>
    <label class="toggle"><input type="checkbox" id="publicOnly"/> Public only</label>
    <label class="toggle"><input type="checkbox" id="privateOnly"/> Private only</label>
    <span class="pill info" id="scope"></span>
  </div>
  <p class="muted" style="margin:10px 0 0">{copy_mod.TAG_HELP}. Selecting a tag scopes to namespaces that contain projects with that tag. Direct/transitive and public/private use DependencyMetadata flags.</p>
</div>
<div class="stats" id="stats"></div>
<div class="callout" id="callout"></div>
<div class="card">
  <div class="card-h">Where version inventory sits</div>
  <p class="caption">Packages grouped by how many distinct versions are in use. Source: DependencyMetadata list_groups (package name × resolved version × direct × public).</p>
  <div class="chart-box"><canvas id="histChart"></canvas></div>
</div>
<div class="card">
  <div class="card-h">Per-ecosystem summary</div>
  <p class="caption">Package and version counts for the current namespace / tag / relation / visibility filters (ecosystem column is not constrained by the ecosystem dropdown).</p>
  <table class="data" id="ecoTable"><thead><tr>
    <th>Ecosystem</th><th class="num">Packages</th><th class="num">Versions</th>
    <th class="num">Avg ver/pkg</th><th class="num">Max</th>
  </tr></thead><tbody></tbody></table>
</div>
<h2>Packages with the most versions in use</h2>
<p class="caption">Top packages by distinct versions under the active filters.</p>
<table class="data" id="topTable"><thead><tr><th>Package</th><th class="num">Versions in use</th></tr></thead><tbody></tbody></table>
<script>
{_chart_helpers_js()}
const CUBE = {payload};
const HIST_LABELS = {{"1":"1 version","2-3":"2–3 versions","4-5":"4–5 versions","6-10":"6–10 versions","11-25":"11–25 versions","26+":"26+ versions"}};
function emptyCell() {{ return {{p:0,v:0,max:0,avg:0,h:[0,0,0,0,0,0],hv:[0,0,0,0,0,0],t:[]}}; }}
function relationMode() {{
  const d = document.getElementById("direct").checked;
  const t = document.getElementById("transitive").checked;
  if (d && !t) return "direct";
  if (t && !d) return "transitive";
  return "all";
}}
function visibilityMode() {{
  const pub = document.getElementById("publicOnly").checked;
  const priv = document.getElementById("privateOnly").checked;
  if (pub && !priv) return "public";
  if (priv && !pub) return "private";
  return "all";
}}
function cellAt(map, eco, relation, visibility) {{
  const node = (map||{{}})[eco||"all"];
  if (!node) return emptyCell();
  // New shape: [eco][relation][visibility]
  if (node[relation] && typeof node[relation] === "object" && ("all" in node[relation] || "public" in node[relation] || "private" in node[relation] || visibility in node[relation])) {{
    return node[relation][visibility] || emptyCell();
  }}
  // Legacy shape: [eco][relation] was the cell itself (relation key "all" only)
  if (node[relation] && typeof node[relation].p === "number") return node[relation];
  if (node.all && typeof node.all.p === "number") return node.all;
  return emptyCell();
}}
function resolveCell(eco, ns, tag, relation, visibility) {{
  eco = eco || "all";
  if (tag && tag !== "all") return cellAt(CUBE.perTag[tag], eco, relation, visibility);
  if (ns && ns !== "all") return cellAt(CUBE.perPath[ns], eco, relation, visibility);
  return cellAt(CUBE.estate, eco, relation, visibility);
}}
function fillSelect(el, options) {{
  el.innerHTML = options.map(o => `<option value="${{o.v}}">${{o.l}}</option>`).join("");
}}
let histChart;
function render() {{
  const theme = chartTheme();
  const eco = document.getElementById("eco").value;
  const ns = document.getElementById("ns").value;
  const tag = document.getElementById("tag").value;
  const relation = relationMode();
  const visibility = visibilityMode();
  const cell = resolveCell(eco, ns, tag, relation, visibility);
  const bits = [];
  if (ns !== "all") bits.push(ns);
  if (tag !== "all") bits.push("tag:" + tag);
  if (eco !== "all") bits.push(eco);
  if (relation === "direct") bits.push("direct only");
  if (relation === "transitive") bits.push("transitive only");
  if (visibility === "public") bits.push("public only");
  if (visibility === "private") bits.push("private only");
  document.getElementById("scope").textContent = bits.length ? bits.join(" · ") : "Entire organization";
  document.getElementById("stats").innerHTML = `
    <div class="stat info"><b>${{cell.p.toLocaleString()}}</b><span>Distinct packages</span></div>
    <div class="stat"><b>${{cell.v.toLocaleString()}}</b><span>Distinct package versions</span></div>
    <div class="stat"><b>${{cell.avg}}</b><span>Avg versions per package</span></div>
    <div class="stat${{cell.max>=50?" warn":""}}"><b>${{cell.max}}</b><span>Most versions for one package</span></div>`;
  document.getElementById("callout").textContent =
    `${{cell.p.toLocaleString()}} packages · ${{cell.v.toLocaleString()}} versions in scope.`;
  const labels = (CUBE.histKeys||[]).map(k => HIST_LABELS[k]||k);
  if (histChart) histChart.destroy();
  histChart = new Chart(document.getElementById("histChart"), {{
    type: "bar",
    data: {{
      labels,
      datasets: [
        {{ label: "Versions in those packages", data: cell.hv||cell.h, backgroundColor: theme.accent + "99" }},
        {{ label: "Packages in band", data: cell.h, backgroundColor: theme.secondary + "99" }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{ legend: {{ labels: {{ color: theme.muted }} }} }},
      scales: chartScales(theme)
    }}
  }});
  const ecos = ["all", ...(CUBE.ecosystems||[])];
  document.querySelector("#ecoTable tbody").innerHTML = ecos.map(e => {{
    const c = resolveCell(e, ns, tag, relation, visibility);
    const label = e === "all" ? "All ecosystems" : e;
    return `<tr><td>${{label}}</td><td class="num">${{(c.p||0).toLocaleString()}}</td>
      <td class="num">${{(c.v||0).toLocaleString()}}</td>
      <td class="num">${{c.avg ?? 0}}</td><td class="num">${{(c.max||0).toLocaleString()}}</td></tr>`;
  }}).join("");
  const top = cell.t || [];
  document.querySelector("#topTable tbody").innerHTML = top.length
    ? top.map(([n,v]) => `<tr><td>${{n}}</td><td class="num"><b>${{v}}</b></td></tr>`).join("")
    : `<tr><td colspan="2" class="muted">No top list for this slice</td></tr>`;
}}
fillSelect(document.getElementById("ns"), [
  {{v:"all", l:"All namespaces"}},
  ...(CUBE.pathOptions||[]).filter(p => p!=="all").map(p => ({{v:p,l:p}}))
]);
fillSelect(document.getElementById("tag"), [
  {{v:"all", l:"All project tags"}},
  ...(CUBE.tags||[]).map(t => ({{v:t.tag, l:`${{t.tag}} (${{t.projectCount}} projects)`}}))
]);
fillSelect(document.getElementById("eco"), [
  {{v:"all", l:"All ecosystems"}},
  ...(CUBE.ecosystems||[]).map(e => ({{v:e,l:e}}))
]);
function wireExclusive(a, b) {{
  document.getElementById(a).addEventListener("change", () => {{
    if (document.getElementById(a).checked) document.getElementById(b).checked = false;
    render();
  }});
}}
["ns","tag","eco"].forEach(id => document.getElementById(id).addEventListener("change", render));
wireExclusive("direct", "transitive");
wireExclusive("transitive", "direct");
wireExclusive("publicOnly", "privateOnly");
wireExclusive("privateOnly", "publicOnly");
render();
</script>
""",
        title=f"{copy_mod.H1_VERSION_SPRAWL} — {tenant}",
    )


def _render_sca_burndown(cube: dict[str, Any]) -> str:
    tenant = cube.get("tenant") or ""
    pulled = cube.get("pulledAt") or ""
    report = _sca_burndown_report(cube)
    # Slim throughput topProjects to names only for size
    tp = report.get("throughput") or {}
    per_tag = {}
    for tag, scope in (tp.get("perTag") or {}).items():
        per_tag[tag] = {
            "projectCount": scope.get("projectCount"),
            "mainScans91d": scope.get("mainScans91d"),
            "ciRunScans21d": scope.get("ciRunScans21d"),
            "avgMainScansPerProject": scope.get("avgMainScansPerProject"),
            "avgMainPerWeek": scope.get("avgMainPerWeek"),
            "topProjects": [
                {
                    "name": p.get("name"),
                    "namespace": p.get("namespace"),
                    "mainScans91d": p.get("mainScans91d"),
                    "ciRunScans21d": p.get("ciRunScans21d"),
                }
                for p in (scope.get("topProjects") or [])[:8]
            ],
        }
    slim = {
        "tenant": tenant,
        "pulledAt": pulled,
        "findingCriteria": report.get("findingCriteria"),
        "lookback": report.get("lookback"),
        "pathOptions": cube.get("pathOptions") or ["all"],
        "tagCatalog": [
            {"tag": t["tag"], "projectCount": t["projectCount"]}
            for t in (cube.get("tagCatalog") or [])
        ],
        "tagSeriesMeta": cube.get("tagSeriesMeta") or report.get("tagSeriesMeta"),
        "seriesFilters": report.get("seriesFilters"),
        "tagSeries": report.get("tagSeries"),
        "throughput": {
            "windows": tp.get("windows"),
            "perPath": {
                k: {
                    "projectCount": v.get("projectCount"),
                    "mainScans91d": v.get("mainScans91d"),
                    "ciRunScans21d": v.get("ciRunScans21d"),
                    "avgMainScansPerProject": v.get("avgMainScansPerProject"),
                    "avgMainPerWeek": v.get("avgMainPerWeek"),
                }
                for k, v in (tp.get("perPath") or {}).items()
            },
            "perTag": per_tag,
        },
    }
    payload = json.dumps(slim, separators=(",", ":"))
    pending_caption = copy_mod.PENDING_TAG_CAPTION
    window_net = copy_mod.STAT_WINDOW_NET
    main_label = copy_mod.MAIN_THROUGHPUT_LABEL
    avg_scans_label = copy_mod.AVG_SCANS_PER_PROJECT_LABEL
    tag_help = copy_mod.TAG_HELP
    gap_diff_help = copy_mod.GAP_DIFF_HELP
    leaders_narrow = copy_mod.TAG_LEADERS_NARROWING
    leaders_widen = copy_mod.TAG_LEADERS_WIDENING
    return _page(
        f"""{_nav("sca")}
{_header(title=copy_mod.H1_SCA_BURNDOWN, purpose=copy_mod.PURPOSE_SCA_BURNDOWN, tenant=tenant, pulled_at=pulled)}
{copy_mod.GLOSSARY_HTML}
<div class="card">
  <div class="card-h">Filters</div>
  <div class="filters">
    <label class="field">Namespace<select id="ns"></select></label>
    <label class="field">Project tag<select id="tag"></select></label>
    <label class="field">Severity<select id="sev"></select></label>
    <label class="field">Reachability<select id="reach"></select></label>
  </div>
  <div class="toggles" id="pills"></div>
  <p class="muted" style="margin:10px 0 0">{tag_help}. Tag selection scopes to projects that carry that tag.</p>
</div>
<div id="body"></div>
<script>
{_chart_helpers_js()}
const CUBE = {payload};
const PENDING_CAPTION = {json.dumps(pending_caption)};
const WINDOW_NET = {json.dumps(window_net)};
const MAIN_LABEL = {json.dumps(main_label)};
const AVG_SCANS_LABEL = {json.dumps(avg_scans_label)};
const GAP_DIFF_HELP = {json.dumps(gap_diff_help)};
const LEADERS_NARROW = {json.dumps(leaders_narrow)};
const LEADERS_WIDEN = {json.dumps(leaders_widen)};
const LEADER_LIMIT = 10;
function pathKey(ns) {{ return ns && ns !== "all" ? ns : "all"; }}
function resolveSeries(ns, sev, reach, tag) {{
  let matrix = null;
  if (tag && tag !== "all" && CUBE.tagSeries?.perTag?.[tag]) {{
    matrix = CUBE.tagSeries.perTag[tag][pathKey(ns)] ?? null;
  }} else {{
    matrix = CUBE.seriesFilters?.perPath?.[pathKey(ns)] ?? null;
  }}
  return resolveSevCell(matrix, sev, reach);
}}
function resolveTp(ns, tag) {{
  if (tag && tag !== "all") return CUBE.throughput?.perTag?.[tag] ?? null;
  return CUBE.throughput?.perPath?.[pathKey(ns)] ?? null;
}}
function fillSelect(el, options) {{
  el.innerHTML = options.map(o => `<option value="${{o.v}}">${{o.l}}</option>`).join("");
}}
function tagLabel(t) {{
  if (t === "all") return "All project tags";
  const cat = (CUBE.tagCatalog||[]).find(r => r.tag === t);
  const pc = cat?.projectCount;
  const ready = !!(CUBE.tagSeries?.perTag?.[t]);
  const base = pc != null ? `${{t}} (${{pc}} projects)` : t;
  return ready ? base : `${{base}} — series pending`;
}}
function signed(n) {{
  const v = Number(n) || 0;
  if (v > 0) return `+${{v.toLocaleString()}}`;
  return v.toLocaleString();
}}
function gapTrendLabel(cell) {{
  const start = Number(cell.gapStart) || 0;
  const end = Number(cell.gapEnd) || 0;
  const delta = end - start;
  if (delta > 0) return `Widening (${{signed(delta)}})`;
  if (delta < 0) return `Narrowing (${{signed(delta)}})`;
  return "Stable (0)";
}}
function gapTrendClass(cell) {{
  const delta = (Number(cell.gapEnd) || 0) - (Number(cell.gapStart) || 0);
  if (delta > 0) return "warn";
  if (delta < 0) return "ok";
  return "";
}}
function tagGapRows(ns, sev, reach) {{
  const pk = pathKey(ns);
  const catalog = Object.fromEntries((CUBE.tagCatalog||[]).map(r => [r.tag, r.projectCount]));
  const rows = [];
  for (const [tag, pathMap] of Object.entries(CUBE.tagSeries?.perTag || {{}})) {{
    const cell = resolveSevCell(pathMap?.[pk], sev, reach);
    if (!cell) continue;
    const gapStart = Number(cell.gapStart) || 0;
    const gapEnd = Number(cell.gapEnd) || 0;
    rows.push({{
      tag,
      projectCount: catalog[tag] ?? 0,
      gapStart,
      gapEnd,
      delta: gapEnd - gapStart,
    }});
  }}
  return rows;
}}
function leaderTable(rows, selectedTag) {{
  if (!rows.length) {{
    return `<p class="muted">No tagged series for this filter combination.</p>`;
  }}
  const body = rows.map(r => {{
    const deltaCls = r.delta > 0 ? "delta-widen" : (r.delta < 0 ? "delta-narrow" : "");
    const sel = r.tag === selectedTag ? " selected" : "";
    return `<tr class="clickable${{sel}}" data-tag="${{r.tag}}">
      <td>${{r.tag}}</td>
      <td class="num">${{(r.projectCount||0).toLocaleString()}}</td>
      <td class="num">${{r.gapStart.toLocaleString()}}</td>
      <td class="num">${{r.gapEnd.toLocaleString()}}</td>
      <td class="num ${{deltaCls}}">${{signed(r.delta)}}</td>
    </tr>`;
  }}).join("");
  return `<table class="data"><thead><tr>
    <th>Tag</th><th class="num">Projects</th>
    <th class="num">Gap start</th><th class="num">Gap end</th>
    <th class="num">Δ gap</th>
  </tr></thead><tbody>${{body}}</tbody></table>`;
}}
function tagLeaderboardsHtml(ns, sev, reach, selectedTag) {{
  const rows = tagGapRows(ns, sev, reach);
  if (!rows.length) return "";
  const narrowing = [...rows].filter(r => r.delta < 0).sort((a,b) => a.delta - b.delta).slice(0, LEADER_LIMIT);
  const widening = [...rows].filter(r => r.delta > 0).sort((a,b) => b.delta - a.delta).slice(0, LEADER_LIMIT);
  return `<div class="card">
    <div class="card-h">Tag gap leaders</div>
    <p class="caption">${{GAP_DIFF_HELP}} Ranked for the current namespace / severity / reachability filters (all tags with series). Click a row to focus that tag.</p>
    <div class="grid-2">
      <div>
        <div class="card-h">${{LEADERS_NARROW}}</div>
        ${{leaderTable(narrowing, selectedTag)}}
      </div>
      <div>
        <div class="card-h">${{LEADERS_WIDEN}}</div>
        ${{leaderTable(widening, selectedTag)}}
      </div>
    </div>
  </div>`;
}}
function throughputStatsHtml(tp, pending) {{
  if (!tp) return "";
  const mainDays = CUBE.throughput?.windows?.mainDays ?? 91;
  const avg = tp.avgMainScansPerProject;
  const avgText = (avg == null || Number.isNaN(Number(avg)))
    ? "—"
    : Number(avg).toLocaleString(undefined, {{ maximumFractionDigits: 2 }});
  const win = CUBE.throughput?.windows || {{}};
  const last = win.lastScanAt ? String(win.lastScanAt).slice(0, 19).replace("T", " ") + "Z" : null;
  const oldest = win.oldestScanAt ? String(win.oldestScanAt).slice(0, 10) : null;
  const ret = win.observedRetentionDays;
  const boundBits = [];
  if (last) boundBits.push(`newest ScanResult ${{last}}`);
  if (oldest) boundBits.push(`oldest retained ${{oldest}}`);
  if (ret != null) boundBits.push(`~${{ret}}d observed history`);
  const bound = boundBits.length
    ? `<p class="caption">Scan history bounds: ${{boundBits.join(" · ")}}. MAIN window is ${{mainDays}}d (must fit inside retained history).</p>`
    : "";
  return `<div class="stats">
    <div class="stat"><b>${{(tp.projectCount||0).toLocaleString()}}</b><span>${{pending ? "Projects with tag" : "Projects in scope"}}</span></div>
    <div class="stat"><b>${{(tp.mainScans91d||0).toLocaleString()}}</b><span>${{MAIN_LABEL}} (${{mainDays}}d)</span></div>
    <div class="stat info"><b>${{avgText}}</b><span>${{AVG_SCANS_LABEL}} (${{mainDays}}d)</span></div>
    <div class="stat"><b>${{(tp.ciRunScans21d||0).toLocaleString()}}</b><span>CI / PR scans (21d)</span></div>
  </div>${{bound}}`;
}}
function wireLeaderClicks(root) {{
  root.querySelectorAll("tr.clickable[data-tag]").forEach(tr => {{
    tr.addEventListener("click", () => {{
      const tag = tr.getAttribute("data-tag");
      const sel = document.getElementById("tag");
      if (tag && sel) {{ sel.value = tag; render(); }}
    }});
  }});
}}
let gapChart, weekChart;
function destroyCharts() {{
  if (gapChart) {{ gapChart.destroy(); gapChart = null; }}
  if (weekChart) {{ weekChart.destroy(); weekChart = null; }}
}}
function render() {{
  const theme = chartTheme();
  const ns = document.getElementById("ns").value;
  const tag = document.getElementById("tag").value;
  const sev = document.getElementById("sev").value;
  const reach = document.getElementById("reach").value;
  const cell = resolveSeries(ns, sev, reach, tag);
  const tp = resolveTp(ns, tag);
  const bits = [];
  if (ns === "all") bits.push("Entire organization"); else bits.push(ns);
  if (tag !== "all") bits.push("tag:" + tag);
  if (sev !== "high_plus") bits.push(SEV_LABELS[sev] || sev);
  if (reach !== "all") {{
    const reachLabels = {{
      reachable: "reachable function",
      prf: "PRF",
      prd: "PRD",
      unreachable: "unreachable",
      unreachable_function: "unreachable function",
      unreachable_dependency: "unreachable dependency",
    }};
    bits.push(reachLabels[reach] || reach);
  }}
  document.getElementById("pills").innerHTML = `<span class="pill info">${{bits.join(" · ")}}</span>`;
  destroyCharts();
  const body = document.getElementById("body");
  const leaders = tagLeaderboardsHtml(ns, sev, reach, tag);
  const pending = tag !== "all" && !CUBE.tagSeries?.perTag?.[tag];
  if (pending) {{
    body.innerHTML = `<div class="callout warn">${{PENDING_CAPTION}}</div>` +
      throughputStatsHtml(tp, true) + leaders;
    wireLeaderClicks(body);
    return;
  }}
  if (!cell) {{
    body.innerHTML = `<div class="callout warn">No trend series for this filter combination.</div>` + leaders;
    wireLeaderClicks(body);
    return;
  }}
  const lastNew = cell.weeklyNew.at(-1) || 0;
  const lastRes = cell.weeklyResolved.at(-1) || 0;
  const trendLabel = gapTrendLabel(cell);
  const trendCls = gapTrendClass(cell);
  body.innerHTML = `<div class="stats">
    <div class="stat ${{cell.gapEnd>0?"warn":"ok"}}"><b>${{cell.gapEnd.toLocaleString()}}</b><span>${{WINDOW_NET}}</span></div>
    <div class="stat"><b>${{lastNew.toLocaleString()}}</b><span>New (last week)</span></div>
    <div class="stat info"><b>${{lastRes.toLocaleString()}}</b><span>Resolved (last week)</span></div>
    <div class="stat ${{trendCls}}"><b>${{trendLabel}}</b><span>Gap trend</span></div>
  </div>
  ${{throughputStatsHtml(tp, false)}}
  <div class="card"><div class="card-h">Cumulative new vs resolved · window net</div>
    <p class="caption">Source: FindingLog CREATE/DELETE · ${{CUBE.findingCriteria||""}} · ${{cell.periodCaption||""}} · filters: ${{bits.join(" · ")}}</p>
    <div class="chart-box"><canvas id="gapChart"></canvas></div></div>
  <div class="card"><div class="card-h">Weekly new vs resolved</div>
    <p class="caption">Weekly FindingLog event counts under the same filters.</p>
    <div class="chart-box sm"><canvas id="weekChart"></canvas></div></div>
  ${{leaders}}`;
  wireLeaderClicks(body);
  const cats = (cell.categories||[]).map(c => String(c).slice(0,12));
  const opts = {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ labels: {{ color: theme.muted }} }} }},
    scales: chartScales(theme)
  }};
  gapChart = new Chart(document.getElementById("gapChart"), {{
    type: "line",
    data: {{
      labels: cats,
      datasets: [
        {{ label: "Cumulative new", data: cell.cumulativeNew, borderColor: theme.danger, tension: 0.2 }},
        {{ label: "Cumulative resolved", data: cell.cumulativeResolved, borderColor: theme.ok, tension: 0.2 }},
        {{ label: "Window net", data: cell.gaps, borderColor: theme.warn, borderDash: [4,4], tension: 0.2 }},
      ]
    }},
    options: opts
  }});
  weekChart = new Chart(document.getElementById("weekChart"), {{
    type: "bar",
    data: {{
      labels: cats,
      datasets: [
        {{ label: "New", data: cell.weeklyNew, backgroundColor: theme.danger + "99" }},
        {{ label: "Resolved", data: cell.weeklyResolved, backgroundColor: theme.ok + "99" }},
      ]
    }},
    options: opts
  }});
}}
fillSelect(document.getElementById("ns"), [
  {{v:"all", l:"All namespaces"}},
  ...(CUBE.pathOptions||[]).filter(p => p!=="all").map(p => ({{v:p,l:p}}))
]);
fillSelect(document.getElementById("tag"), [
  {{v:"all", l:"All project tags"}},
  ...(CUBE.tagCatalog||[]).map(t => ({{v:t.tag, l: tagLabel(t.tag)}}))
]);
fillSelect(document.getElementById("sev"), SEV_OPTIONS);
document.getElementById("sev").value = "high_plus";
fillSelect(document.getElementById("reach"), [
  {{v:"all", l:"All reachability (RF + PRF)"}},
  {{v:"reachable", l:"Reachable function only"}},
  {{v:"prf", l:"Potentially reachable function (PRF)"}},
  {{v:"prd", l:"Potentially reachable dependency (PRD)"}},
  {{v:"unreachable", l:"Unreachable (function + dependency)"}},
  {{v:"unreachable_function", l:"Unreachable function only"}},
  {{v:"unreachable_dependency", l:"Unreachable dependency only"}},
]);
["ns","tag","sev","reach"].forEach(id => document.getElementById(id).addEventListener("change", render));
render();
</script>
""",
        title=f"{copy_mod.H1_SCA_BURNDOWN} — {tenant}",
    )


def _render_sast_burndown(cube: dict[str, Any]) -> str:
    tenant = cube.get("tenant") or ""
    pulled = cube.get("pulledAt") or ""
    report = (cube.get("reports") or {}).get("codeFindingsBurndown") or {}
    slim = {
        "tenant": tenant,
        "pulledAt": pulled,
        "lookback": report.get("lookback"),
        "periodCaption": report.get("periodCaption"),
        "pathOptions": cube.get("pathOptions") or ["all"],
        "tagCatalog": [
            {"tag": t["tag"], "projectCount": t["projectCount"]}
            for t in (cube.get("tagCatalog") or [])
        ],
        "tagSeriesMeta": report.get("tagSeriesMeta") or cube.get("tagSeriesMeta"),
        "byCategory": report.get("byCategory") or {},
        "categories": report.get("categories") or ["sast", "ai_sast", "secrets"],
    }
    payload = json.dumps(slim, separators=(",", ":"))
    pending_caption = copy_mod.PENDING_TAG_CAPTION
    window_net = copy_mod.STAT_WINDOW_NET
    tag_help = copy_mod.TAG_HELP
    gap_diff_help = copy_mod.GAP_DIFF_HELP
    leaders_narrow = copy_mod.TAG_LEADERS_NARROWING
    leaders_widen = copy_mod.TAG_LEADERS_WIDENING
    return _page(
        f"""{_nav("sast")}
{_header(title=copy_mod.H1_SAST_BURNDOWN, purpose=copy_mod.PURPOSE_SAST_BURNDOWN, tenant=tenant, pulled_at=pulled)}
{copy_mod.GLOSSARY_HTML}
<div class="card">
  <div class="card-h">Filters</div>
  <div class="filters">
    <label class="field">Namespace<select id="ns"></select></label>
    <label class="field">Project tag<select id="tag"></select></label>
    <label class="field">Category<select id="category"></select></label>
    <label class="field">Severity<select id="sev"></select></label>
    <label class="field" id="facetField">Facet<select id="facet"></select></label>
  </div>
  <div class="toggles" id="pills"></div>
  <p class="muted" style="margin:10px 0 0">{tag_help}. Tag selection scopes to projects that carry that tag.</p>
</div>
<div id="body"></div>
<script>
{_chart_helpers_js()}
const CUBE = {payload};
const PENDING_CAPTION = {json.dumps(pending_caption)};
const WINDOW_NET = {json.dumps(window_net)};
const GAP_DIFF_HELP = {json.dumps(gap_diff_help)};
const LEADERS_NARROW = {json.dumps(leaders_narrow)};
const LEADERS_WIDEN = {json.dumps(leaders_widen)};
const LEADER_LIMIT = 10;
const FACET_OPTIONS = {{
  sast: [
    {{v:"all", l:"All (category)"}},
    {{v:"true_positive", l:"True positive"}},
    {{v:"false_positive", l:"False positive"}},
  ],
  ai_sast: [
    {{v:"all", l:"All AI-SAST"}},
  ],
  secrets: [
    {{v:"all", l:"All secrets"}},
    {{v:"valid", l:"Valid secret"}},
    {{v:"invalid", l:"Invalid secret"}},
  ],
}};
const CATEGORY_LABELS = {{
  sast: "SAST (OpenGrep)",
  ai_sast: "AI-SAST (detection)",
  secrets: "Secrets",
}};
function pathKey(ns) {{ return ns && ns !== "all" ? ns : "all"; }}
function catBlock() {{
  const key = document.getElementById("category").value;
  return CUBE.byCategory?.[key] || null;
}}
function resolveSeries(ns, sev, facet, tag) {{
  const block = catBlock();
  if (!block) return null;
  let matrix = null;
  if (tag && tag !== "all" && block.tagSeries?.perTag?.[tag]) {{
    matrix = block.tagSeries.perTag[tag][pathKey(ns)] ?? null;
  }} else {{
    matrix = block.seriesFilters?.perPath?.[pathKey(ns)] ?? null;
  }}
  return resolveSevCell(matrix, sev, facet);
}}
function fillSelect(el, options) {{
  el.innerHTML = options.map(o => `<option value="${{o.v}}">${{o.l}}</option>`).join("");
}}
function tagLabel(t) {{
  if (t === "all") return "All project tags";
  const cat = (CUBE.tagCatalog||[]).find(r => r.tag === t);
  const pc = cat?.projectCount;
  const block = catBlock();
  const ready = !!(block?.tagSeries?.perTag?.[t]);
  const base = pc != null ? `${{t}} (${{pc}} projects)` : t;
  return ready ? base : `${{base}} — series pending`;
}}
function signed(n) {{
  const v = Number(n) || 0;
  if (v > 0) return `+${{v.toLocaleString()}}`;
  return v.toLocaleString();
}}
function gapTrendLabel(cell) {{
  const start = Number(cell.gapStart) || 0;
  const end = Number(cell.gapEnd) || 0;
  const delta = end - start;
  if (delta > 0) return `Widening (${{signed(delta)}})`;
  if (delta < 0) return `Narrowing (${{signed(delta)}})`;
  return "Stable (0)";
}}
function gapTrendClass(cell) {{
  const delta = (Number(cell.gapEnd) || 0) - (Number(cell.gapStart) || 0);
  if (delta > 0) return "warn";
  if (delta < 0) return "ok";
  return "";
}}
function tagGapRows(ns, sev, facet) {{
  const pk = pathKey(ns);
  const catalog = Object.fromEntries((CUBE.tagCatalog||[]).map(r => [r.tag, r.projectCount]));
  const block = catBlock();
  const rows = [];
  for (const [tag, pathMap] of Object.entries(block?.tagSeries?.perTag || {{}})) {{
    const cell = resolveSevCell(pathMap?.[pk], sev, facet);
    if (!cell) continue;
    const gapStart = Number(cell.gapStart) || 0;
    const gapEnd = Number(cell.gapEnd) || 0;
    rows.push({{
      tag,
      projectCount: catalog[tag] ?? 0,
      gapStart,
      gapEnd,
      delta: gapEnd - gapStart,
    }});
  }}
  return rows;
}}
function leaderTable(rows, selectedTag) {{
  if (!rows.length) {{
    return `<p class="muted">No tagged series for this filter combination.</p>`;
  }}
  const body = rows.map(r => {{
    const deltaCls = r.delta > 0 ? "delta-widen" : (r.delta < 0 ? "delta-narrow" : "");
    const sel = r.tag === selectedTag ? " selected" : "";
    return `<tr class="clickable${{sel}}" data-tag="${{r.tag}}">
      <td>${{r.tag}}</td>
      <td class="num">${{(r.projectCount||0).toLocaleString()}}</td>
      <td class="num">${{r.gapStart.toLocaleString()}}</td>
      <td class="num">${{r.gapEnd.toLocaleString()}}</td>
      <td class="num ${{deltaCls}}">${{signed(r.delta)}}</td>
    </tr>`;
  }}).join("");
  return `<table class="data"><thead><tr>
    <th>Tag</th><th class="num">Projects</th>
    <th class="num">Gap start</th><th class="num">Gap end</th>
    <th class="num">Δ gap</th>
  </tr></thead><tbody>${{body}}</tbody></table>`;
}}
function tagLeaderboardsHtml(ns, sev, facet, selectedTag) {{
  const rows = tagGapRows(ns, sev, facet);
  if (!rows.length) return "";
  const narrowing = [...rows].filter(r => r.delta < 0).sort((a,b) => a.delta - b.delta).slice(0, LEADER_LIMIT);
  const widening = [...rows].filter(r => r.delta > 0).sort((a,b) => b.delta - a.delta).slice(0, LEADER_LIMIT);
  return `<div class="card">
    <div class="card-h">Tag gap leaders</div>
    <p class="caption">${{GAP_DIFF_HELP}} Ranked for the current filters. Click a row to focus that tag.</p>
    <div class="grid-2">
      <div>
        <div class="card-h">${{LEADERS_NARROW}}</div>
        ${{leaderTable(narrowing, selectedTag)}}
      </div>
      <div>
        <div class="card-h">${{LEADERS_WIDEN}}</div>
        ${{leaderTable(widening, selectedTag)}}
      </div>
    </div>
  </div>`;
}}
function wireLeaderClicks(root) {{
  root.querySelectorAll("tr.clickable[data-tag]").forEach(tr => {{
    tr.addEventListener("click", () => {{
      const tag = tr.getAttribute("data-tag");
      const sel = document.getElementById("tag");
      if (tag && sel) {{ sel.value = tag; render(); }}
    }});
  }});
}}
function syncFacetOptions() {{
  const cat = document.getElementById("category").value;
  const opts = FACET_OPTIONS[cat] || FACET_OPTIONS.sast;
  const facetEl = document.getElementById("facet");
  const prev = facetEl.value;
  fillSelect(facetEl, opts);
  if (opts.some(o => o.v === prev)) facetEl.value = prev;
  document.getElementById("facetField").style.display =
    opts.length <= 1 ? "none" : "";
}}
let gapChart, weekChart;
function destroyCharts() {{
  if (gapChart) {{ gapChart.destroy(); gapChart = null; }}
  if (weekChart) {{ weekChart.destroy(); weekChart = null; }}
}}
function render() {{
  const theme = chartTheme();
  syncFacetOptions();
  const ns = document.getElementById("ns").value;
  const tag = document.getElementById("tag").value;
  const category = document.getElementById("category").value;
  const sev = document.getElementById("sev").value;
  const facet = document.getElementById("facet").value;
  const block = catBlock();
  const cell = resolveSeries(ns, sev, facet, tag);
  const bits = [];
  if (ns === "all") bits.push("Entire organization"); else bits.push(ns);
  if (tag !== "all") bits.push("tag:" + tag);
  bits.push(CATEGORY_LABELS[category] || category);
  if (sev !== "high_plus") bits.push(SEV_LABELS[sev] || sev);
  if (facet !== "all") bits.push(facet.replaceAll("_", " "));
  document.getElementById("pills").innerHTML = `<span class="pill info">${{bits.join(" · ")}}</span>`;
  destroyCharts();
  const body = document.getElementById("body");
  const leaders = tagLeaderboardsHtml(ns, sev, facet, tag);
  const pending = tag !== "all" && !block?.tagSeries?.perTag?.[tag];
  if (!block || !(Object.keys(CUBE.byCategory||{{}}).length)) {{
    body.innerHTML = `<div class="callout warn">No code-findings burndown series in this packet (skipped or empty).</div>`;
    return;
  }}
  if (pending) {{
    body.innerHTML = `<div class="callout warn">${{PENDING_CAPTION}}</div>` + leaders;
    wireLeaderClicks(body);
    return;
  }}
  if (!cell) {{
    body.innerHTML = `<div class="callout warn">No trend series for this filter combination.</div>` + leaders;
    wireLeaderClicks(body);
    return;
  }}
  const lastNew = cell.weeklyNew.at(-1) || 0;
  const lastRes = cell.weeklyResolved.at(-1) || 0;
  const trendLabel = gapTrendLabel(cell);
  const trendCls = gapTrendClass(cell);
  const criteria = block.findingCriteria || "";
  body.innerHTML = `<div class="stats">
    <div class="stat ${{cell.gapEnd>0?"warn":"ok"}}"><b>${{cell.gapEnd.toLocaleString()}}</b><span>${{WINDOW_NET}}</span></div>
    <div class="stat"><b>${{lastNew.toLocaleString()}}</b><span>New (last week)</span></div>
    <div class="stat info"><b>${{lastRes.toLocaleString()}}</b><span>Resolved (last week)</span></div>
    <div class="stat ${{trendCls}}"><b>${{trendLabel}}</b><span>Gap trend</span></div>
  </div>
  <div class="card"><div class="card-h">Cumulative new vs resolved · window net</div>
    <p class="caption">Source: FindingLog CREATE/DELETE · ${{criteria}} · ${{cell.periodCaption||""}} · filters: ${{bits.join(" · ")}}</p>
    <div class="chart-box"><canvas id="gapChart"></canvas></div></div>
  <div class="card"><div class="card-h">Weekly new vs resolved</div>
    <p class="caption">Weekly FindingLog event counts under the same filters.</p>
    <div class="chart-box sm"><canvas id="weekChart"></canvas></div></div>
  ${{leaders}}`;
  wireLeaderClicks(body);
  const cats = (cell.categories||[]).map(c => String(c).slice(0,12));
  const opts = {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ labels: {{ color: theme.muted }} }} }},
    scales: chartScales(theme)
  }};
  gapChart = new Chart(document.getElementById("gapChart"), {{
    type: "line",
    data: {{
      labels: cats,
      datasets: [
        {{ label: "Cumulative new", data: cell.cumulativeNew, borderColor: theme.danger, tension: 0.2 }},
        {{ label: "Cumulative resolved", data: cell.cumulativeResolved, borderColor: theme.ok, tension: 0.2 }},
        {{ label: "Window net", data: cell.gaps, borderColor: theme.warn, borderDash: [4,4], tension: 0.2 }},
      ]
    }},
    options: opts
  }});
  weekChart = new Chart(document.getElementById("weekChart"), {{
    type: "bar",
    data: {{
      labels: cats,
      datasets: [
        {{ label: "New", data: cell.weeklyNew, backgroundColor: theme.danger + "99" }},
        {{ label: "Resolved", data: cell.weeklyResolved, backgroundColor: theme.ok + "99" }},
      ]
    }},
    options: opts
  }});
}}
fillSelect(document.getElementById("ns"), [
  {{v:"all", l:"All namespaces"}},
  ...(CUBE.pathOptions||[]).filter(p => p!=="all").map(p => ({{v:p,l:p}}))
]);
fillSelect(document.getElementById("tag"), [
  {{v:"all", l:"All project tags"}},
  ...(CUBE.tagCatalog||[]).map(t => ({{v:t.tag, l: tagLabel(t.tag)}}))
]);
fillSelect(document.getElementById("category"), [
  {{v:"sast", l:"SAST (OpenGrep)"}},
  {{v:"ai_sast", l:"AI-SAST (detection)"}},
  {{v:"secrets", l:"Secrets"}},
]);
fillSelect(document.getElementById("sev"), SEV_OPTIONS);
document.getElementById("sev").value = "high_plus";
syncFacetOptions();
["ns","tag","category","sev","facet"].forEach(id => document.getElementById(id).addEventListener("change", render));
render();
</script>
""",
        title=f"{copy_mod.H1_SAST_BURNDOWN} — {tenant}",
    )


_render_findings_burndown = _render_sca_burndown


def render_report_packet(
    cube: dict[str, Any],
    out_dir: str | Path,
) -> list[Path]:
    """Write HTML packet + cube JSON + raw CSV exports + README under *out_dir*.

    Returns paths written (assets, HTML, cube, CSVs, README).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    files = [
        (out / "01-onboarding.html", _render_onboarding(cube)),
        (out / "02-version-sprawl.html", _render_version_sprawl(cube)),
        (out / "03-sca-burndown.html", _render_sca_burndown(cube)),
        (out / "04-sast-burndown.html", _render_sast_burndown(cube)),
        (data_dir / "packet.cube.json", json.dumps(cube, indent=2) + "\n"),
        (out / "README.txt", copy_mod.README_TEXT),
    ]
    written: list[Path] = list(_copy_shell_assets(out))
    for path, content in files:
        safe_write_text(out, path, content)
        written.append(path)
    written.extend(write_packet_raw_exports(cube, data_dir))
    return written


def default_packet_output_dir(namespace: str) -> Path:
    """Default ``runs/executive-report-packet/<tenant>-executive-packet`` path."""
    from endorlabs.context.paths import default_runs_dir

    slug = sanitize_path_segment(namespace)
    return default_runs_dir(RUN_BUCKET) / f"{slug}-executive-packet"
