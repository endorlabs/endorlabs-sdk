#!/usr/bin/env python3
"""Generate an interactive HTML report from a package-resolution CSV.

Self-contained browser artifact (Endor executive-report styling): filters for
ecosystem, matching rule, error stage (unresolved / resolved / call graph),
fixable, namespace, and text search; live stats + charts + paginated table.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any

from endorlabs.context.paths import default_runs_dir, sanitize_path_segment

RUN_BUCKET = "package-resolution"
PAGE_SIZE = 100

# Compact row indices
I_NS = 0
I_UUID = 1
I_NAME = 2
I_ECO = 3
I_AV = 4
I_V = 5
I_AD = 6
I_D = 7
I_CAT = 8
I_RULE = 9
I_FIX = 10
I_NOTES = 11
I_FULL = 12
I_UNRES = 13
I_RES = 14
I_CG = 15
I_ERR_U = 16
I_ERR_R = 17
I_ERR_C = 18
I_PROJ = 19
I_TAGS = 20
I_URL = 21

SUCCESS_MAP = {"": 0, "TRUE": 1, "FALSE": 2, "N/A": 3}
FIX_MAP = {"": 0, "TRUE": 1, "FALSE": 2}
SUCCESS_LABELS = ["", "TRUE", "FALSE", "N/A"]
FIX_LABELS = ["", "TRUE", "FALSE"]


def _tokens_css() -> str:
    root = resources.files("endorlabs.workflows.reports.export.html.shell")
    return (root / "tokens.css").read_text(encoding="utf-8")


def _copy_assets(out_dir: Path) -> None:
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    root = resources.files("endorlabs.workflows.reports.export.html.shell")
    for name in ("endor-logo.png", "endor-wordmark.png", "chart.umd.min.js"):
        with resources.as_file(root / "assets" / name) as src:
            shutil.copyfile(src, assets / name)


def _dict_index(values: list[str], value: str) -> int:
    try:
        return values.index(value)
    except ValueError:
        values.append(value)
        return len(values) - 1


def _to_int(value: str) -> int:
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def load_csv(path: Path) -> tuple[list[list[Any]], dict[str, Any]]:
    namespaces: list[str] = []
    ecosystems: list[str] = []
    categories: list[str] = [""]
    rules: list[str] = [""]
    projects: list[str] = [""]
    err_statuses: list[str] = [""]

    rows: list[list[Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            ns = (raw.get("Namespace") or "").strip()
            eco = (raw.get("PackageVersion Ecosystem") or "").strip()
            cat = (raw.get("Resolution Error Category") or "").strip()
            rule = (raw.get("Resolution Error Type") or "").strip()
            proj = (raw.get("Project Name") or "").strip()
            fix = (raw.get("Fixable") or "").strip().upper()
            if fix not in FIX_MAP:
                fix = ""
            full = (raw.get("Full Success") or "").strip().upper()
            unres = (raw.get("Unresolved Success") or "").strip().upper()
            res = (raw.get("Resolved Success") or "").strip().upper()
            cg = (raw.get("Call Graph Success") or "").strip().upper()
            err_u = (raw.get("Resolution Error (Unresolved)") or "").strip()
            err_r = (raw.get("Resolution Error (Resolved)") or "").strip()
            err_c = (raw.get("Resolution Error (Call Graph)") or "").strip()
            notes = (raw.get("Fixable Notes") or "").strip()
            # Keep notes only when there is an error signal (shrink payload).
            if full == "TRUE" and not cat and not rule:
                notes = ""

            rows.append(
                [
                    _dict_index(namespaces, ns),
                    (raw.get("PackageVersion UUID") or "").strip(),
                    (raw.get("PackageVersion Name") or "").strip(),
                    _dict_index(ecosystems, eco),
                    _to_int(raw.get("Num Approximated Vulns") or ""),
                    _to_int(raw.get("Num Vulns") or ""),
                    _to_int(raw.get("Num Approximated Dependencies") or ""),
                    _to_int(raw.get("Num Dependencies") or ""),
                    _dict_index(categories, cat),
                    _dict_index(rules, rule),
                    FIX_MAP.get(fix, 0),
                    notes,
                    SUCCESS_MAP.get(full, 0),
                    SUCCESS_MAP.get(unres, 0),
                    SUCCESS_MAP.get(res, 0),
                    SUCCESS_MAP.get(cg, 0),
                    _dict_index(err_statuses, err_u),
                    _dict_index(err_statuses, err_r),
                    _dict_index(err_statuses, err_c),
                    _dict_index(projects, proj),
                    (raw.get("Project Tags") or "").strip(),
                    (raw.get("Endor URL") or "").strip(),
                ]
            )

    # Mutually exclusive primary stage (priority: unresolved/manifest →
    # dependency resolution → reachability → full success).
    dist_full = dist_unres = dist_dep = dist_reach = 0
    no_best_match = 0
    for r in rows:
        has_error = r[I_FULL] == 2
        if has_error and r[I_RULE] == 0:
            no_best_match += 1
        if r[I_UNRES] == 2:
            dist_unres += 1
        elif r[I_RES] == 2:
            dist_dep += 1
        elif r[I_CG] == 2:
            dist_reach += 1
        else:
            dist_full += 1

    meta = {
        "namespaces": namespaces,
        "ecosystems": ecosystems,
        "categories": categories,
        "rules": rules,
        "projects": projects,
        "errStatuses": err_statuses,
        "successLabels": SUCCESS_LABELS,
        "fixLabels": FIX_LABELS,
        "rowCount": len(rows),
        "fullSuccess": sum(1 for r in rows if r[I_FULL] == 1),
        "fullFailure": sum(1 for r in rows if r[I_FULL] == 2),
        "unresolvedFalse": sum(1 for r in rows if r[I_UNRES] == 2),
        "resolvedFalse": sum(1 for r in rows if r[I_RES] == 2),
        "callGraphFalse": sum(1 for r in rows if r[I_CG] == 2),
        "fixableTrue": sum(1 for r in rows if r[I_FIX] == 1),
        "fixableFalse": sum(1 for r in rows if r[I_FIX] == 2),
        "noBestMatch": no_best_match,
        "distribution": {
            "fullSuccess": dist_full,
            "unresolvedManifest": dist_unres,
            "dependencyResolution": dist_dep,
            "reachability": dist_reach,
        },
        "ecosystemCounts": dict(Counter(ecosystems[r[I_ECO]] for r in rows)),
        "ruleCounts": dict(Counter(rules[r[I_RULE]] for r in rows if r[I_RULE] > 0)),
    }
    return rows, meta


def _extra_css() -> str:
    return """
.wrap { max-width: 1400px; }
.filters { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
input[type="search"], input[type="text"] {
  background: var(--endor-bg); color: var(--endor-text);
  border: 1px solid var(--endor-border); border-radius: 6px;
  padding: 7px 10px; font-size: 0.85rem;
}
.table-wrap { overflow: auto; max-height: 620px; border: 1px solid var(--endor-border); border-radius: 8px; }
table.data { margin: 0; }
table.data th { position: sticky; top: 0; z-index: 1; }
table.data td a { color: var(--endor-accent); text-decoration: none; }
table.data td a:hover { text-decoration: underline; }
.pager {
  display: flex; gap: 10px; align-items: center; justify-content: space-between;
  margin-top: 10px; flex-wrap: wrap;
}
.pager button {
  background: var(--endor-panel); color: var(--endor-text);
  border: 1px solid var(--endor-border); border-radius: 6px;
  padding: 6px 12px; font-size: 0.8rem; cursor: pointer;
}
.pager button:disabled { opacity: 0.4; cursor: default; }
.pager button:not(:disabled):hover { border-color: var(--endor-accent); }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 999px;
  border: 1px solid var(--endor-border); font-size: 0.72rem;
}
.badge.ok { color: var(--endor-ok); border-color: var(--endor-ok); }
.badge.warn { color: var(--endor-warn); border-color: var(--endor-warn); }
.badge.danger { color: var(--endor-danger); border-color: var(--endor-danger); }
.badge.muted { color: var(--endor-muted); }
.detail {
  white-space: nowrap; max-width: 280px; overflow: hidden; text-overflow: ellipsis;
}
.detail.notes { max-width: 360px; }
.chart-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
}
.chart-grid-3 {
  display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 14px;
}
@media (max-width: 1100px) {
  .chart-grid, .chart-grid-3 { grid-template-columns: 1fr; }
}
.chart-box.pie { height: 300px; }
.reset-btn {
  background: transparent; color: var(--endor-muted);
  border: 1px dashed var(--endor-border); border-radius: 6px;
  padding: 6px 12px; font-size: 0.78rem; cursor: pointer;
}
.reset-btn:hover { color: var(--endor-text); border-color: var(--endor-accent); }
"""


def render_html(
    *,
    tenant: str,
    source_csv: str,
    rows: list[list[Any]],
    meta: dict[str, Any],
    generated_at: str,
) -> str:
    payload = {
        "tenant": tenant,
        "sourceCsv": source_csv,
        "generatedAt": generated_at,
        "pageSize": PAGE_SIZE,
        "meta": meta,
        "rows": rows,
    }
    data_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Package resolution · {tenant}</title>
<script src="assets/chart.umd.min.js"></script>
<style>{_tokens_css()}
{_extra_css()}
</style>
</head>
<body>
<div class="wrap">
<header class="site-header">
  <img class="brand-wordmark" src="assets/endor-wordmark.png" alt="Endor Labs"/>
  <span class="brand-tag">Package resolution</span>
</header>
<h1>Package resolution analysis</h1>
<p class="purpose">Main-context PackageVersion inventory with unresolved/manifest, dependency resolution, and reachability error signals. Filter interactively; open Endor URL for package inventory.</p>
<p class="meta">Namespace <strong>{tenant}</strong> · Generated {generated_at[:10]} · Source CSV <code>{source_csv}</code> · {meta["rowCount"]:,} rows</p>

<div class="glossary">
  <div class="glossary-title">How to read success flags</div>
  <ul>
    <li><strong>Unresolved/manifest</strong> — FALSE when unresolved/manifest errors exist; otherwise TRUE.</li>
    <li><strong>Dependency resolution</strong> — FALSE when dependency-resolution errors exist; N/A when unresolved/manifest errors exist first; otherwise TRUE.</li>
    <li><strong>Reachability</strong> — FALSE when reachability (call-graph) errors exist and neither unresolved/manifest nor dependency-resolution errors exist; otherwise N/A or TRUE.</li>
    <li><strong>Matching rule / Fixable</strong> — from platform <code>error_analysis_best_match</code>. <strong>No best match</strong> = any resolution error with an empty matching rule.</li>
    <li><strong>Distribution pie</strong> — mutually exclusive primary stage (priority: unresolved/manifest → dependency resolution → reachability → full success).</li>
  </ul>
</div>

<div class="card">
  <div class="card-h">Filters</div>
  <div class="filters">
    <label class="field">Namespace<select id="ns"></select></label>
    <label class="field">Ecosystem<select id="eco"></select></label>
    <label class="field">Matching rule<select id="rule"></select></label>
    <label class="field">Error category<select id="cat"></select></label>
    <label class="field">Error stage<select id="stage">
      <option value="all">All packages</option>
      <option value="any_error">Any resolution error (Full Success = FALSE)</option>
      <option value="unresolved">Unresolved/manifest errors</option>
      <option value="resolved">Dependency resolution errors</option>
      <option value="call_graph">Reachability errors</option>
      <option value="no_best_match">No best match</option>
      <option value="full_success">Full success only</option>
    </select></label>
    <label class="field">Fixable<select id="fix">
      <option value="all">All</option>
      <option value="TRUE">TRUE</option>
      <option value="FALSE">FALSE</option>
      <option value="empty">Empty / unset</option>
    </select></label>
    <label class="field">Search package / project<input type="search" id="q" placeholder="name contains…"/></label>
  </div>
  <div class="toggles" style="margin-top:12px">
    <button type="button" class="reset-btn" id="reset">Reset filters</button>
    <span class="pill info" id="scope"></span>
  </div>
</div>

<div class="stats" id="stats"></div>

<div class="chart-grid-3">
  <div class="card">
    <div class="card-h">Outcome distribution</div>
    <p class="caption">Primary stage under current filters (mutually exclusive).</p>
    <div class="chart-box pie"><canvas id="distChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-h">Filtered rows by ecosystem</div>
    <p class="caption">Counts under the current filter set.</p>
    <div class="chart-box sm"><canvas id="ecoChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-h">Top matching rules</div>
    <p class="caption">Non-empty <code>error_analysis_best_match.matching_rule</code> under current filters.</p>
    <div class="chart-box sm"><canvas id="ruleChart"></canvas></div>
  </div>
</div>

<div class="card">
  <div class="card-h">PackageVersions</div>
  <p class="caption">Paginated detail for the filtered set. Click Endor to open inventory.</p>
  <div class="table-wrap">
    <table class="data" id="tbl">
      <thead>
        <tr>
          <th>Package</th>
          <th>Ecosystem</th>
          <th>Namespace</th>
          <th>Stage</th>
          <th>Matching rule</th>
          <th>Fixable</th>
          <th class="num">Deps</th>
          <th class="num">Vulns</th>
          <th>Project</th>
          <th></th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="pager">
    <button type="button" id="prev">Previous</button>
    <span class="muted" id="pageLabel"></span>
    <button type="button" id="next">Next</button>
  </div>
</div>

<footer class="site-footer">
  <img class="footer-mark" src="assets/endor-logo.png" alt="" width="28" height="28"/>
  <p class="footer-copy">Generated by the Endor Labs SDK · package resolution interactive report · not the live product UI</p>
</footer>
</div>

<script>
const DATA = {data_json};
const M = DATA.meta;
const ROWS = DATA.rows;
const PAGE = DATA.pageSize || 100;
const I = {{
  NS:0, UUID:1, NAME:2, ECO:3, AV:4, V:5, AD:6, D:7, CAT:8, RULE:9, FIX:10,
  NOTES:11, FULL:12, UNRES:13, RES:14, CG:15, ERR_U:16, ERR_R:17, ERR_C:18,
  PROJ:19, TAGS:20, URL:21
}};

function brandVar(name) {{
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}}
function chartTheme() {{
  return {{
    muted: brandVar("--endor-muted"),
    grid: brandVar("--endor-border"),
    accent: brandVar("--endor-accent"),
    ok: brandVar("--endor-ok"),
    warn: brandVar("--endor-warn"),
    danger: brandVar("--endor-danger"),
    neutral: brandVar("--endor-chart-neutral"),
    secondary: brandVar("--endor-chart-secondary"),
  }};
}}
function esc(s) {{
  return String(s ?? "").replace(/[&<>"']/g, c => ({{
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }})[c]);
}}
function shortEco(e) {{
  return String(e || "").replace(/^ECOSYSTEM_/, "");
}}
function fillSelect(el, values, blankLabel) {{
  const opts = [`<option value="">${{blankLabel}}</option>`];
  for (const v of values) {{
    if (!v) continue;
    opts.push(`<option value="${{esc(v)}}">${{esc(v)}}</option>`);
  }}
  el.innerHTML = opts.join("");
}}

const nsEl = document.getElementById("ns");
const ecoEl = document.getElementById("eco");
const ruleEl = document.getElementById("rule");
const catEl = document.getElementById("cat");
const stageEl = document.getElementById("stage");
const fixSelect = document.getElementById("fix");
const qEl = document.getElementById("q");

fillSelect(nsEl, [...M.namespaces].sort(), "All namespaces");
fillSelect(ecoEl, [...M.ecosystems].sort(), "All ecosystems");
fillSelect(ruleEl, [...M.rules].filter(Boolean).sort(), "All matching rules");
fillSelect(catEl, [...M.categories].filter(Boolean).sort(), "All categories");

let filtered = ROWS.slice();
let page = 0;
let ecoChart, ruleChart, distChart;

function primaryStage(row) {{
  // Mutually exclusive: unresolved/manifest → dependency resolution → reachability → full success
  if (row[I.UNRES] === 2) return "unresolved";
  if (row[I.RES] === 2) return "resolved";
  if (row[I.CG] === 2) return "call_graph";
  return "full_success";
}}

function hasNoBestMatch(row) {{
  return row[I.FULL] === 2 && row[I.RULE] === 0;
}}

function matches(row) {{
  const ns = nsEl.value;
  const eco = ecoEl.value;
  const rule = ruleEl.value;
  const cat = catEl.value;
  const stage = stageEl.value;
  const fix = fixSelect.value;
  const q = (qEl.value || "").trim().toLowerCase();

  if (ns && M.namespaces[row[I.NS]] !== ns) return false;
  if (eco && M.ecosystems[row[I.ECO]] !== eco) return false;
  if (rule && M.rules[row[I.RULE]] !== rule) return false;
  if (cat && M.categories[row[I.CAT]] !== cat) return false;

  if (fix === "TRUE" && row[I.FIX] !== 1) return false;
  if (fix === "FALSE" && row[I.FIX] !== 2) return false;
  if (fix === "empty" && row[I.FIX] !== 0) return false;

  if (stage === "any_error" && row[I.FULL] !== 2) return false;
  if (stage === "full_success" && row[I.FULL] !== 1) return false;
  if (stage === "unresolved" && row[I.UNRES] !== 2) return false;
  if (stage === "resolved" && row[I.RES] !== 2) return false;
  if (stage === "call_graph" && row[I.CG] !== 2) return false;
  if (stage === "no_best_match" && !hasNoBestMatch(row)) return false;

  if (q) {{
    const name = String(row[I.NAME] || "").toLowerCase();
    const proj = String(M.projects[row[I.PROJ]] || "").toLowerCase();
    const uuid = String(row[I.UUID] || "").toLowerCase();
    if (!name.includes(q) && !proj.includes(q) && !uuid.includes(q)) return false;
  }}
  return true;
}}

function stageBadges(row) {{
  const bits = [];
  if (row[I.UNRES] === 2) bits.push('<span class="badge danger">unresolved/manifest</span>');
  if (row[I.RES] === 2) bits.push('<span class="badge warn">dependency resolution</span>');
  if (row[I.CG] === 2) bits.push('<span class="badge warn">reachability</span>');
  if (!bits.length) {{
    if (row[I.FULL] === 1) return '<span class="badge ok">full success</span>';
    return '<span class="badge muted">—</span>';
  }}
  if (hasNoBestMatch(row)) bits.push('<span class="badge muted">no best match</span>');
  return bits.join(" ");
}}

function fixBadge(row) {{
  const v = M.fixLabels[row[I.FIX]] || "";
  if (v === "TRUE") return '<span class="badge ok">TRUE</span>';
  if (v === "FALSE") return '<span class="badge danger">FALSE</span>';
  return '<span class="badge muted">—</span>';
}}

function renderStats() {{
  const n = filtered.length;
  const fullOk = filtered.filter(r => r[I.FULL] === 1).length;
  const fullBad = filtered.filter(r => r[I.FULL] === 2).length;
  const u = filtered.filter(r => r[I.UNRES] === 2).length;
  const r = filtered.filter(r => r[I.RES] === 2).length;
  const c = filtered.filter(r => r[I.CG] === 2).length;
  const ft = filtered.filter(r => r[I.FIX] === 1).length;
  const ff = filtered.filter(r => r[I.FIX] === 2).length;
  const nbm = filtered.filter(hasNoBestMatch).length;
  document.getElementById("stats").innerHTML = `
    <div class="stat info"><b>${{n.toLocaleString()}}</b><span>Filtered rows</span></div>
    <div class="stat ok"><b>${{fullOk.toLocaleString()}}</b><span>Full success</span></div>
    <div class="stat warn"><b>${{fullBad.toLocaleString()}}</b><span>Any resolution error</span></div>
    <div class="stat"><b>${{u.toLocaleString()}}</b><span>Unresolved/manifest = FALSE</span></div>
    <div class="stat"><b>${{r.toLocaleString()}}</b><span>Dependency resolution = FALSE</span></div>
    <div class="stat"><b>${{c.toLocaleString()}}</b><span>Reachability = FALSE</span></div>
    <div class="stat"><b>${{nbm.toLocaleString()}}</b><span>No best match</span></div>
    <div class="stat ok"><b>${{ft.toLocaleString()}}</b><span>Fixable = TRUE</span></div>
    <div class="stat danger"><b>${{ff.toLocaleString()}}</b><span>Fixable = FALSE</span></div>
  `;
  document.getElementById("scope").textContent =
    `${{n.toLocaleString()}} of ${{ROWS.length.toLocaleString()}} PackageVersions`;
}}

function topCounts(getter, limit=12) {{
  const c = new Map();
  for (const row of filtered) {{
    const k = getter(row);
    if (!k) continue;
    c.set(k, (c.get(k) || 0) + 1);
  }}
  return [...c.entries()].sort((a,b) => b[1]-a[1]).slice(0, limit);
}}

function distributionCounts() {{
  let fullSuccess = 0, unresolvedManifest = 0, dependencyResolution = 0, reachability = 0;
  for (const row of filtered) {{
    const stage = primaryStage(row);
    if (stage === "unresolved") unresolvedManifest += 1;
    else if (stage === "resolved") dependencyResolution += 1;
    else if (stage === "call_graph") reachability += 1;
    else fullSuccess += 1;
  }}
  return {{ fullSuccess, unresolvedManifest, dependencyResolution, reachability }};
}}

function renderCharts() {{
  const theme = chartTheme();
  const eco = topCounts(r => shortEco(M.ecosystems[r[I.ECO]]), 10);
  const rules = topCounts(r => M.rules[r[I.RULE]], 10);
  const dist = distributionCounts();

  const ecoCfg = {{
    type: "bar",
    data: {{
      labels: eco.map(x => x[0]),
      datasets: [{{
        label: "PackageVersions",
        data: eco.map(x => x[1]),
        backgroundColor: theme.accent + "99"
      }}]
    }},
    options: {{
      indexAxis: "y",
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: theme.muted }}, grid: {{ color: theme.grid }} }},
        y: {{ ticks: {{ color: theme.muted }}, grid: {{ display: false }} }}
      }}
    }}
  }};
  const ruleCfg = {{
    type: "bar",
    data: {{
      labels: rules.map(x => x[0]),
      datasets: [{{
        label: "PackageVersions",
        data: rules.map(x => x[1]),
        backgroundColor: theme.warn + "99"
      }}]
    }},
    options: {{
      indexAxis: "y",
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ ticks: {{ color: theme.muted }}, grid: {{ color: theme.grid }} }},
        y: {{ ticks: {{ color: theme.muted }}, grid: {{ display: false }} }}
      }}
    }}
  }};
  const distLabels = [
    "Full success",
    "Unresolved/manifest",
    "Dependency resolution",
    "Reachability"
  ];
  const distValues = [
    dist.fullSuccess,
    dist.unresolvedManifest,
    dist.dependencyResolution,
    dist.reachability
  ];
  const distCfg = {{
    type: "pie",
    data: {{
      labels: distLabels,
      datasets: [{{
        data: distValues,
        backgroundColor: [
          theme.ok,
          theme.danger,
          theme.warn,
          theme.accent
        ],
        borderColor: theme.grid,
        borderWidth: 1
      }}]
    }},
    options: {{
      plugins: {{
        legend: {{
          position: "bottom",
          labels: {{ color: theme.muted, boxWidth: 12, padding: 12 }}
        }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => {{
              const total = distValues.reduce((a, b) => a + b, 0) || 1;
              const v = ctx.raw || 0;
              const pct = ((v / total) * 100).toFixed(1);
              return `${{ctx.label}}: ${{Number(v).toLocaleString()}} (${{pct}}%)`;
            }}
          }}
        }}
      }}
    }}
  }};
  if (ecoChart) ecoChart.destroy();
  if (ruleChart) ruleChart.destroy();
  if (distChart) distChart.destroy();
  ecoChart = new Chart(document.getElementById("ecoChart"), ecoCfg);
  ruleChart = new Chart(document.getElementById("ruleChart"), ruleCfg);
  distChart = new Chart(document.getElementById("distChart"), distCfg);
}}

function renderTable() {{
  const start = page * PAGE;
  const slice = filtered.slice(start, start + PAGE);
  const body = document.querySelector("#tbl tbody");
  body.innerHTML = slice.map(row => {{
    const rule = M.rules[row[I.RULE]] || "";
    const notes = row[I.NOTES] || "";
    const title = notes ? ` title="${{esc(notes)}}"` : "";
    const url = row[I.URL] || "";
    const link = url
      ? `<a href="${{esc(url)}}" target="_blank" rel="noopener">Open</a>`
      : "";
    return `<tr>
      <td class="detail" title="${{esc(row[I.NAME])}}">${{esc(row[I.NAME])}}</td>
      <td>${{esc(shortEco(M.ecosystems[row[I.ECO]]))}}</td>
      <td class="detail" title="${{esc(M.namespaces[row[I.NS]])}}">${{esc(M.namespaces[row[I.NS]])}}</td>
      <td>${{stageBadges(row)}}</td>
      <td class="detail"${{title}}>${{esc(rule || "—")}}</td>
      <td>${{fixBadge(row)}}</td>
      <td class="num">${{Number(row[I.D]).toLocaleString()}}</td>
      <td class="num">${{Number(row[I.V]).toLocaleString()}}</td>
      <td class="detail" title="${{esc(M.projects[row[I.PROJ]] || "")}}">${{esc(M.projects[row[I.PROJ]] || "—")}}</td>
      <td>${{link}}</td>
    </tr>`;
  }}).join("");

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  document.getElementById("pageLabel").textContent =
    `Page ${{page + 1}} / ${{pages}} · showing ${{slice.length}} row(s)`;
  document.getElementById("prev").disabled = page <= 0;
  document.getElementById("next").disabled = page >= pages - 1;
}}

function apply() {{
  filtered = ROWS.filter(matches);
  page = 0;
  renderStats();
  renderCharts();
  renderTable();
}}

nsEl.addEventListener("change", apply);
ecoEl.addEventListener("change", apply);
ruleEl.addEventListener("change", apply);
catEl.addEventListener("change", apply);
stageEl.addEventListener("change", apply);
fixSelect.addEventListener("change", apply);
let qTimer = null;
qEl.addEventListener("input", () => {{
  clearTimeout(qTimer);
  qTimer = setTimeout(apply, 150);
}});
document.getElementById("prev").addEventListener("click", () => {{
  if (page > 0) {{ page -= 1; renderTable(); }}
}});
document.getElementById("next").addEventListener("click", () => {{
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  if (page < pages - 1) {{ page += 1; renderTable(); }}
}});
document.getElementById("reset").addEventListener("click", () => {{
  nsEl.value = "";
  ecoEl.value = "";
  ruleEl.value = "";
  catEl.value = "";
  stageEl.value = "all";
  fixSelect.value = "all";
  qEl.value = "";
  apply();
}});

apply();
</script>
</body>
</html>
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate interactive package-resolution HTML from CSV."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Input package-resolution CSV path.",
    )
    parser.add_argument(
        "--tenant",
        default=None,
        help="Tenant label for the report header (default: inferred from CSV name).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory "
            "(default: workspace/runs/package-resolution/<tenant>-html/)."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    csv_path = args.csv
    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")

    tenant = args.tenant
    if not tenant:
        stem = csv_path.stem
        tenant = stem.replace("-package-resolution", "") or "tenant"

    out_dir = args.output_dir
    if out_dir is None:
        safe = sanitize_path_segment(tenant)
        out_dir = default_runs_dir(RUN_BUCKET) / f"{safe}-html"

    out_dir.mkdir(parents=True, exist_ok=True)
    _copy_assets(out_dir)

    print(f"Loading {csv_path}…", flush=True)
    rows, meta = load_csv(csv_path)
    print(
        f"Loaded {len(rows):,} rows · "
        f"{len(meta['namespaces'])} namespaces · "
        f"{len(meta['ecosystems'])} ecosystems",
        flush=True,
    )

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    html = render_html(
        tenant=tenant,
        source_csv=csv_path.name,
        rows=rows,
        meta=meta,
        generated_at=generated_at,
    )
    out_html = out_dir / "package-resolution.html"
    out_html.write_text(html, encoding="utf-8")
    summary = {
        "tenant": tenant,
        "csv": str(csv_path),
        "html": str(out_html),
        "row_count": meta["rowCount"],
        "full_success": meta["fullSuccess"],
        "full_failure": meta["fullFailure"],
        "resolved_false": meta["resolvedFalse"],
        "no_best_match": meta["noBestMatch"],
        "distribution": meta["distribution"],
        "html_bytes": out_html.stat().st_size,
        "generated_at": generated_at,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"Open: {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
