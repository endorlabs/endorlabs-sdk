---
name: endor-depr-coverage
description: |
  Use when generating a tenant-wide dependency-resolution (DEPR) coverage executive
  report or multi-checkpoint progress report from main-context PackageVersion
  inventory. Writes dated JSON, Markdown, and HTML under the DEPR coverage report
  directory. Not for scan-history reconstruction of past coverage, single
  project RCA, or PRF reachability reports.
---

# Dependency-resolution (DEPR) coverage reports

Produce executive **DEPR Coverage** (point-in-time) and **DEPR Progress**
(checkpoint comparison) reports for a tenant’s first-level namespaces.

1. Query live `Project` + main-context `PackageVersion` inventory via SDK facades.
2. Classify projects (0 packages / 0% DR / partial / full) and org-level failure themes.
3. Write **dated** JSON + technical Markdown + executive Markdown + executive HTML.
4. Optionally build a **progress** report from two or more dated JSON checkpoints
   (Markdown + HTML).

**Artifact-first:** Progress reuses existing `{tenant}__dr_coverage__*.json`
checkpoints — do not re-pull the estate unless the user asks for a new daily
coverage run.

**Not scan history:** PackageVersion inventory is **not** time-travelable. Past
dates require dated JSON snapshots (or a prior run). Scan History / `ScanResult`
stats are a different metric — do not substitute them for this KPI.

**Not estate pull:** Do not run `endor-estate pull` for this report.

## Scope

**In scope**

- Tenant-wide first-level namespace DEPR coverage (package % and fully healthy rate).
- Org-level failure themes from `error_analysis_best_match.matching_rule` + ecosystem.
- Dated JSON / Markdown / HTML deliverables via `endor-reports`.
- Progress across dated checkpoints (exclude gap-repo and “failed packages cleared”
  outcome rows unless the user explicitly asks to restore them).

**Out of scope**

- Reconstructing historical coverage from Scan History alone (not supported).
- Scan pipeline RCA → [endor-troubleshooting-scans](../../skills/endor-troubleshooting-scans/SKILL.md)
- PRF parent PV resolution / call-graph cohorts → [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md)
- Individual findings or policy validation → [endor-retrieve-scan-results](../../skills/endor-retrieve-scan-results/SKILL.md), [endor-validate-policy](../../skills/endor-validate-policy/SKILL.md)

## Methodology (normative)

| Rule | Detail |
| --- | --- |
| Namespace fan-out | Discover first-level children under `<tenant>`; for each child use `Client(tenant=<tenant>.<child>)` with `traverse=True`. Tenant-root projects: exact namespace match, no traverse. |
| Main context | `pv_main_context_filter()` on PackageVersion lists. |
| Fail a PV | `spec.resolution_errors.unresolved` **or** `.resolved` present (call-graph-only errors alone do not fail DR). |
| Coverage % | `packages_resolved / packages_total` among projects with ≥1 package (empty repos excluded). |
| Fully healthy % | Full-resolution projects / projects with packages. |
| Themes | Map `matching_rule` + ecosystem → remediation theme (Artifactory, multimodule Maven, Composer, npm, NuGet, PyPI, …). |
| Writes | **Dated only** — refuse overwrite; never write `*_latest*` pointers. |

## Quick start

Credentials: `ENDOR_TOKEN` or API key/secret (do not print secrets).

### Daily coverage (today)

```bash
uv run --env-file .env endor-reports depr-coverage -n <tenant>
```

### Progress from dated checkpoints

```bash
uv run --env-file .env endor-reports depr-progress -n <tenant> \
  --dates 20260101,20260115,20260201
```

Or pass explicit JSON paths:

```bash
uv run --env-file .env endor-reports depr-progress -n <tenant> \
  --from-json <path-a.json> <path-b.json> <path-c.json>
```

## Outputs

Default directory: `.endorlabs/reports/depr-coverage/`

| File | Description |
| --- | --- |
| `{tenant}__dr_coverage__{ts}.json` | Full aggregates (checkpoint source of truth) |
| `{tenant}__dr_coverage__{ts}.md` | Technical markdown |
| `{tenant}__dr_coverage_EXEC__{ts}.md` | Executive markdown |
| `{tenant}__dr_coverage_EXEC__{ts}.html` | Executive HTML (cards + charts) |
| `{tenant}__dr_coverage_progress__{ts}.json` | Ordered checkpoints used for progress |
| `{tenant}__dr_coverage_progress_EXEC__{ts}.md` | Progress executive markdown |
| `{tenant}__dr_coverage_progress_EXEC__{ts}.html` | Progress executive HTML |

Do not commit generated artifacts.

## Agent workflow

1. Confirm tenant (`-n <tenant>`). Ask if missing.
2. Confirm auth works with a lightweight `Client(tenant=<tenant>)` probe.
3. For **today’s coverage**: run `endor-reports depr-coverage -n <tenant>`.
4. For **progress**: ensure each requested date has a matching
   `{tenant}__dr_coverage__{YYYYMMDD}*.json`. If today’s snapshot is missing,
   run coverage first. Then run `depr-progress --dates …`.
5. Summarize headline metrics and artifact paths (MD + HTML).
6. Do **not** claim Scan History can reproduce prior EXEC coverage %.

## Intake

- Target tenant root namespace.
- Daily coverage vs progress (or both).
- Progress checkpoint dates (`YYYYMMDD`) or explicit JSON paths.
- Output directory override if not using the default report directory.

## SDK modules

| Module | Role |
| --- | --- |
| `endorlabs.workflows.reports.analyze.depr_coverage` | Live API → dated JSON + EXEC MD/HTML |
| `endorlabs.workflows.reports.analyze.depr_progress` | Checkpoints → progress MD/HTML |
| `endorlabs.workflows.reports.export.html.depr_coverage` | Markdown/HTML renderers |

## Related

| Need | Skill / playbook |
| --- | --- |
| Report router | [endor-workflow-reports](../../skills/endor-workflow-reports/SKILL.md) |
| PRF + PV resolution on PRF parents | [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) |
| Scan failure RCA | [endor-troubleshooting-scans](../../skills/endor-troubleshooting-scans/SKILL.md) |
| Auth setup | [endor-auth-setup](../../skills/endor-auth-setup/SKILL.md) |
