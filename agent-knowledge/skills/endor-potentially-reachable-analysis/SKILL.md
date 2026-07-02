---
name: endor-potentially-reachable-analysis
description: >-
  Generates a tenant-wide PRF (potentially reachable function) vulnerability and
  PackageVersion resolution error report for main-context NuGet, NPM, Maven, and
  PyPI findings tagged FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION. Outputs analysis
  JSON, Cursor canvas, and optional HTML/PDF. Use for PRF approximation coverage,
  dependency resolution error triage, or executive-style reachability summaries—not
  for per-finding reachability proof or scan pipeline RCA.
---

# Potentially reachable function (PRF) analysis

Produce the **PRF vulnerability & PV resolution errors — main context** report:

1. Query Finding + PackageVersion APIs via SDK facades (`Finding.list_iter`, `PackageVersion.list_iter`). Default: tenant-wide traverse list with project-shard fallback — **prefer a child namespace when known**; use `--max-pages` to bound list depth per shard.
2. Write analysis JSON.
3. Render an interactive **Cursor canvas** (`.canvas.tsx`).
4. Render matching **HTML + PDF** (headless Chrome).

**Artifact-first:** If `{tenant}-prf-analysis.json` exists and only canvas/PDF refresh is needed, skip `run_analysis.py` and run `generate_canvas.py` / `generate_report_pdf.py` on the saved JSON.

**Not estate pull:** Do not run `endor-estate pull` for this report — it is live API analytics, not workspace-first estate analysis.

## Scope

**In scope**

- Tenant-wide main-context PRF finding counts and approximation split by ecosystem.
- PRF-parent PackageVersion dependency resolution and call graph error cohorts.
- JSON, canvas, HTML, and PDF deliverables via bundled scripts.

**Out of scope**

- Per-finding or per-project reachability proof → [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md), [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md)
- Scan pipeline regression RCA → [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md)
- Individual finding rows or policy validation → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md), [endor-validate-policy](../endor-validate-policy/SKILL.md)

## When to use

- Customer asks for PRF approximation / reachability coverage by ecosystem.
- Triage **dependency resolution errors** or **call graph errors** on PRF-parent PackageVersions.
- Monthly or ad-hoc executive-style report with pie chart, summary table, and per-ecosystem breakdowns.

## Quick start

From the repo root with credentials configured (`ENDOR_TOKEN` or API key/secret):

```bash
uv run python agent-knowledge/skills/endor-potentially-reachable-analysis/scripts/run_report.py \
  <tenant> \
  --output-dir .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis
```

After `init()`, use the materialized skill path:

```bash
uv run python .endorlabs-context/sdk/skills/endor-potentially-reachable-analysis/scripts/run_report.py \
  <tenant> \
  --output-dir .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis
```

Replace `<tenant>` with the tenant root namespace. Child namespaces are included via `list_parameters.traverse=true`.

## Outputs

Under `--output-dir` (default `.endorlabs-context/workspace/sessions/agent/exports/prf-analysis`):

| File | Description |
|------|-------------|
| `{tenant}-prf-analysis.json` | Raw aggregates for regeneration |
| `{tenant}-prf-approximation-main.html` | Dark-theme printable HTML |
| `{tenant}-prf-approximation-main.pdf` | PDF (A3 landscape) |

Canvas (Cursor preview):

| File | Location |
|------|----------|
| `{tenant}-prf-approximation-main.canvas.tsx` | Auto-detected `~/.cursor/projects/<repo-slug>/canvases/`, or `--canvas-dir`, or beside JSON |

Open the canvas in Cursor after generation (Canvas panel).

## Scripts

All under `scripts/`:

| Script | Role |
|--------|------|
| `run_report.py` | Orchestrator: analysis → canvas → PDF |
| `run_analysis.py` | API queries → JSON |
| `generate_canvas.py` | JSON → `.canvas.tsx` |
| `generate_report_pdf.py` | JSON → HTML + PDF |

`run_report.py` flags: `--analysis-only`, `--skip-canvas`, `--html-only` (HTML without PDF), `--skip-pdf` (skip all HTML/PDF output), `--canvas-dir`, `--chrome`.

Run steps individually when iterating on layout without re-querying:

```bash
uv run python .endorlabs-context/sdk/skills/endor-potentially-reachable-analysis/scripts/run_analysis.py \
  <tenant> \
  --output-dir .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis

uv run python .endorlabs-context/sdk/skills/endor-potentially-reachable-analysis/scripts/generate_canvas.py \
  .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis/<tenant>-prf-analysis.json

uv run python .endorlabs-context/sdk/skills/endor-potentially-reachable-analysis/scripts/generate_report_pdf.py \
  .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis/<tenant>-prf-analysis.json \
  --output-dir .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis
```

## Authentication

Same as other SDK tenant workflows:

- `ENDOR_TOKEN`, or `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`
- Prefer a single credential mode; do not print secrets.

## Scope and filters

- **Context:** `CONTEXT_TYPE_MAIN` only unless otherwise asked.
- **Findings base filter:** vulnerability category + `FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION` (PRF).
- **Ecosystems:** NuGet, NPM, Maven, PyPI (`spec.ecosystem` enum filters).
- **Traverse:** all child namespaces under the tenant root.
- **Parent PVs:** unique `meta.parent_uuid` from listed PRF findings; batch-fetched from `package-versions` with `uuid in [...]`.

See [resolution-reference.md](resolution-reference.md) for column definitions and error cohort rules.

## Report contents

The canvas, HTML, and PDF share the same layout:

1. **Pie chart** — PRF vulnerabilities by ecosystem (NuGet, NPM, Maven, PyPI).
2. **Stat row** — total PRF vulns, approximated vulns (%), unique PVs, PVs with dep resolution errors (%).
3. **Combined by ecosystem table** — columns:
   - PRF vulnerabilities
   - PRD vulnerabilities (PRF findings also tagged `FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY`)
   - Approximated / not approximated vulns, % approximated
   - Unique PVs
   - PVs with Dep Resolution errors + %
   - PVs with Call Graph Errors + %
4. **Footnote** — union unique PV count; missing parent PVs excluded from error breakdowns.
5. **Error analysis by ecosystem** (collapsible in canvas) — for each ecosystem:
   - **Dependency resolution errors** — PRF-parent PVs with `resolution_errors.unresolved` or `.resolved`; grouped by `matching_rule`; rows include PRF vulns, PRD vulns, precomputed reachability PV counts.
   - **Call graph errors** — only PVs with `resolution_errors.call_graph` present (same count as summary **PVs with Call Graph Errors**); no “no call graph error” rows; same row metrics as dep resolution.

Internal consistency checks in `run_analysis.py` assert breakdown row counts sum to cohort totals.

## Agent workflow

1. Confirm tenant root and credentials (do not print secrets).
2. Run `run_report.py` with `--output-dir .endorlabs-context/workspace/sessions/<user>/exports/prf-analysis`.
3. Open the generated canvas for interactive review; attach or share the PDF.
4. If PDF fails (no Chrome), use `--html-only` or install Chrome and set `CHROME_PATH`.
5. If canvas auto-detect fails, pass `--canvas-dir` to the Cursor project `canvases/` folder.

## Bounds

- Project-sharded parallel `Finding.list_iter` scoped by **`spec.project_uuid`** (shard key) at each project's `tenant_meta.namespace`. When all projects share one namespace path, a single `traverse=True` query is used instead.
- **`--max-pages`** caps pagination **per project shard**, not globally across the tenant (smoke bounds differ from a single traverse query).
- **`--max-project-pages`** caps project discovery only; truncated discovery omits findings in undiscovered namespaces.
- PackageVersion hydration uses **`traverse=False`** in the project namespace from finding rows; orphan parents fall back to tenant `traverse=True`.
- PDF requires headless Chrome/Chromium (`CHROME_PATH` on Linux).

## When to use this skill vs others

| Goal | Skill |
|------|-------|
| Tenant-wide PRF approximation + PV error summary | **This skill** |
| Per-project call graph path search | [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) |
| Reachability signal conflicts on one finding | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |
| Scan regression / log RCA | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Finding rows for one project | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| New vs resolved FindingLog trend charts | [endor-chart-new-vs-resolved-findings](../endor-chart-new-vs-resolved-findings/SKILL.md) |

## Related skills

| Need | Skill |
| ---- | ----- |
| FindingLog new vs resolved trend charts | [endor-chart-new-vs-resolved-findings](../endor-chart-new-vs-resolved-findings/SKILL.md) |
| Per-project call graph export and path search | [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) |
| Single-finding reachability provenance | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |
| Scan pipeline RCA | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| General finding query patterns | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |

## Documentation hops

- Local API spec: `.endorlabs-context/platform/openapi/openapiv2.swagger.json` (`Finding`, `PackageVersion`, `resolution_errors`).
- Metric definitions: [resolution-reference.md](resolution-reference.md)
