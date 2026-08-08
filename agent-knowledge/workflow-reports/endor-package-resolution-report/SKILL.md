---
name: endor-package-resolution-report
description: |
  Use when producing a tenant-wide main-context PackageVersion resolution report
  (CSV + interactive HTML) covering unresolved/manifest, dependency resolution,
  and reachability error signals with platform error_analysis_best_match fields.
  Not for PRF-only approximation cohorts, single-project RCA, or estate IR collect.
---

# Package resolution report

Produce a **PackageVersion resolution analysis** for one tenant (including child
namespaces):

1. List main-context `PackageVersion` rows (`context.type==CONTEXT_TYPE_MAIN`,
   `traverse=True`).
2. Enrich each row with concurrent scoped counts (`Finding`, `DependencyMetadata`)
   and cached `Project` metadata — **not** a single graph Query join.
3. Write CSV under `.endorlabs-context/workspace/runs/package-resolution/`.
4. Render a self-contained interactive HTML report (Endor executive shell styling)
   with filters and an outcome-distribution pie chart.

**Artifact-first:** If `{tenant}-package-resolution.csv` already exists and only
HTML refresh is needed, use `--html-only --csv <path>`.

**Not estate pull:** Do not run `endor-estate pull` for this report.

## Scope

**In scope**

- Tenant-wide main-context PackageVersion inventory and resolution error stages.
- CSV columns matching the package-resolution handoff schema (see below).
- Interactive HTML with filters: namespace, ecosystem, matching rule, error
  category, error stage, fixable, text search.
- Outcome pie: full success · unresolved/manifest · dependency resolution ·
  reachability (mutually exclusive primary stage).
- **No best match** count (error rows with empty matching rule).

**Out of scope**

- PRF approximation / ecosystem PRF cohorts → [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md)
- Executive onboarding / sprawl / FindingLog burndown packet → [endor-executive-report-packet](../endor-executive-report-packet/SKILL.md)
- Single-project findings → [endor-retrieve-scan-results](../../skills/endor-retrieve-scan-results/SKILL.md)
- Estate IR collect → `endor-estate`

## Terminology (HTML / interpretation)

| UI term | CSV / API source |
|---------|------------------|
| **Unresolved/manifest** | `Unresolved Success` / `spec.resolution_errors.unresolved` |
| **Dependency resolution** | `Resolved Success` / `spec.resolution_errors.resolved` |
| **Reachability** | `Call Graph Success` / `spec.resolution_errors.call_graph` |
| **Matching rule / Fixable** | `error_analysis_best_match` on the primary status object (unresolved → resolved → call_graph) |

Success-flag rules:

- **Unresolved/manifest** — FALSE only when unresolved errors exist; otherwise TRUE.
- **Dependency resolution** — FALSE when resolved-stage errors exist; **N/A** when unresolved/manifest errors exist first; otherwise TRUE.
- **Reachability** — FALSE when call-graph errors exist and neither unresolved nor resolved errors exist; otherwise N/A or TRUE.
- **Full Success** — TRUE only when none of the three error objects exist.

## Privileged read (customer namespaces)

Employee / privileged read against customer tenants uses **endor-admin SSO** for
the bearer token — not the customer namespace as the auth tenant.

```bash
uv run endor-auth refresh --env-file .env-admin --method sso -n endor-admin
uv run --env-file .env-admin endor-auth check --tenant endor-admin
```

Then pass the **customer** namespace only on the report command (never commit
customer names in tracked files):

```bash
uv run --env-file .env-admin endor-reports package-resolution -n <tenant>
```

## Default command

```bash
uv run --env-file .env endor-reports package-resolution -n <tenant>
```

Optional flags:

| Flag | Default | Meaning |
|------|---------|---------|
| `--output` | `workspace/runs/package-resolution/<tenant>-package-resolution.csv` | CSV path |
| `--html-dir` | `workspace/runs/package-resolution/<tenant>-html/` | HTML output directory |
| `--max-workers` | `16` | Concurrent related-object API workers |
| `--max-inflight` | `64` | Max in-flight PackageVersion enrichments |
| `--json-summary` | unset | Optional JSON summary beside the CSV run |
| `--skip-html` | off | CSV only |
| `--html-only` | off | Render HTML from `--csv` (no live API) |
| `--csv` | unset | Existing CSV for `--html-only` |
| `--timeout` | `120` | Client request timeout (seconds) |

HTML-only refresh:

```bash
uv run endor-reports package-resolution -n <tenant> --html-only \
  --csv .endorlabs-context/workspace/runs/package-resolution/<tenant>-package-resolution.csv
```

## Outputs

| File | Content |
|------|---------|
| `<tenant>-package-resolution.csv` | Full tabular export |
| `<tenant>-html/package-resolution.html` | Interactive filters + charts (keep sibling `assets/`) |
| `<tenant>-html/summary.json` | HTML generation summary (row counts, distribution) |

Open the HTML in a browser; keep the `assets/` directory next to the HTML file.

## CSV schema (required columns)

| Column | Source |
|--------|--------|
| Namespace | `tenant_meta.namespace` |
| PackageVersion UUID / Name / Ecosystem | PackageVersion |
| Num Approximated Vulns / Num Vulns | `Finding.count` (`meta.parent_uuid`, vulnerability category; approx flag) |
| Num Approximated Dependencies / Num Dependencies | `DependencyMetadata.count` (`spec.importer_data.package_version_uuid`) |
| Resolution Error Category / Type / Fixable / Fixable Notes | `error_analysis_best_match` |
| Full / Unresolved / Resolved / Call Graph Success | derived from `spec.resolution_errors` |
| Resolution Error (Unresolved/Resolved/Call Graph) status, target, operation | nested status objects |
| Scan State / Scan Time / Analytic Time / Disable Automated Scan | `processing_status` |
| Project UUID / Name / Tags | PackageVersion `spec.project_uuid` + `Project.get` |
| Endor URL | `https://app.endorlabs.com/t/{namespace}/projects/{project_uuid}/versions/default/inventory/packages` |

## Library

```python
from endorlabs import Client
from endorlabs.workflows.reports.analyze.package_resolution import (
    collect_rows,
    write_csv,
)
from endorlabs.workflows.reports.export.html.package_resolution import (
    load_csv,
    render_html,
)

client = Client(tenant="<tenant>")
rows = collect_rows(client, tenant="<tenant>", max_workers=16, max_inflight=64)
client.close()
```

Use placeholders only in tracked examples (`example-tenant`, `<tenant>`).

## Related skills

| Need | Skill |
|------|-------|
| Package resolution CSV + HTML | **This playbook** (via [endor-workflow-reports](../../skills/endor-workflow-reports/SKILL.md)) |
| PRF + PV resolution cohorts | [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) |
| Executive HTML packet | [endor-executive-report-packet](../endor-executive-report-packet/SKILL.md) |
| Auth / SDK setup | [endor-auth-setup](../../skills/endor-auth-setup/SKILL.md) |
