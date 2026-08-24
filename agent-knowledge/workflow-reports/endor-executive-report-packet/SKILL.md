---
name: endor-executive-report-packet
description: |
  Use when producing a tenant-level executive interactive HTML report packet
  (onboarding + scan/PR cadence, dependency version sprawl, SCA and
  SAST/AI-SAST/Secrets FindingLog burndown, Endor Patches) for browser handoff.
  Not for single-project RCA, estate IR collect, or Cursor canvas-only artifacts.
endorlabs:
  catalog:
    workflow_id: executive-report-packet
    module: endorlabs.workflows.reports.cli
    agent_visible: false
    library_entrypoints:
      - endorlabs.workflows.reports.bundles.executive_packet.build_report_packet
      - endorlabs.workflows.reports.export.html.render.render_report_packet
      - endorlabs.workflows.reports.analyze.patches.collect_patches_report
      - endorlabs.workflows.reports.parity.compare_packet_cube
---

# Executive report packet

Build a **self-contained HTML packet** for a tenant or namespace: organization
onboarding (registration + ScanResult MAIN/CI cadence), dependency version
sprawl, FindingLog CREATE/DELETE burndown (SCA + SAST/AI-SAST/Secrets), and
Endor Patches impact. Open the HTML files in any browser — no Cursor runtime
required.

## Scope

**In scope**

- Tenant/namespace executive HTML under
  `.endorlabs-context/workspace/runs/executive-report-packet/<tenant>-executive-packet-MMDDYY/`.
- Project tag discovery from `Project.meta.tags` (full catalog; no allowlists).
- Onboarding scan cadence: weekly MAIN `TYPE_ALL_SCANS` + `CONTEXT_TYPE_CI_RUN`
  (analytics off by default); tag/project leaderboards by cadence.
- FindingLog window-net trends; tag series via project-grain pulls + local
  redistribute (`--workers`); `--min-projects` only filters display.

**Out of scope**

- Single-project findings → [endor-retrieve-scan-results](../../skills/endor-retrieve-scan-results/SKILL.md)
- Estate IR / risk dashboard → `endor-estate`
- Cursor `.canvas.tsx` generation (agent preview only; not the customer deliverable)

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
uv run --env-file .env-admin endor-reports packet -n <tenant>
```

## Default command

```bash
uv run --env-file .env endor-reports packet -n <tenant>
```

Optional flags:

- `--lookback 13` — FindingLog weeks
- `--min-projects 1` — display filter: omit tags with fewer tagged projects
- `--workers 24` — parallel FindingLog matrix pulls for tagged projects
- `--output-dir <path>` — override default runs bucket
- `--date-suffix 082126` — override today's MMDDYY on default dirs
  (`<tenant>-executive-packet-MMDDYY/` or `--patches-only` `<tenant>-MMDDYY/`)
- `--skip-version-sprawl` / `--skip-findings-burndown` / `--skip-patches` —
  partial packets
- `--patches-only` — Endor Patches page only (Finding list); default output
  `.endorlabs-context/workspace/runs/patches-reports/<tenant>-MMDDYY/`. Writes
  only `05-endor-patches.html` + `patches-*.csv`; pages 01–04 are not emitted.
On a live slice failure (e.g. FindingLog timeout), HTML still writes; cube
`dataGaps` / `reportsMeta` name the failed slice; CLI exits `1`.

## Scratch parity (gitignored baselines)

Compare a fresh packet cube to prior session JSON under
`.endorlabs-context/workspace/runs/scratch/` (never commit customer baselines).

Set baseline paths via **environment only** (PowerShell example):

```powershell
$env:ENDOR_VALIDATE_NAMESPACE = '<tenant>'
$env:ENDOR_VALIDATE_ADOPTION_CUBE = '<path-to-adoption-canvas-data.json>'
$env:ENDOR_VALIDATE_VC_CUBE = '<path-to-version-cardinality-cube.json>'
$env:ENDOR_VALIDATE_BURNDOWN_CUBE = '<path-to-findings-burndown-cube.json>'
uv run --env-file .env-admin endor-reports parity -n $env:ENDOR_VALIDATE_NAMESPACE
```

Or pass paths explicitly:

```bash
uv run --env-file .env-admin endor-reports parity \
  -n <tenant> \
  --baseline-adoption <path> \
  --baseline-sprawl <path> \
  --baseline-burndown <path> \
  --output-dir .endorlabs-context/workspace/runs/report-parity/
```

Writes `packet/` (fresh HTML + cube) and `compare-summary.json` (metric deltas
only). Accept small live drift (≤1–2%); fail on structural breaks or large cliffs.

| Scratch artifact | Packet cube path |
|------------------|------------------|
| adoption canvas JSON | `reports.onboarding` (`raw_count` → `allRegistrations`, …) |
| version-cardinality cube | `reports.versionSprawl.estate.all.all` (`packages`→`p`, …) |
| findings-burndown cube | `reports.findingsBurndown` (`gapEnd`, throughput, tag catalog) |

## Outputs

| File | Content |
|------|---------|
| `01-onboarding.html` | Onboarding + scan/PR cadence + tag/project ranks |
| `02-version-sprawl.html` | Dependency version sprawl |
| `03-sca-burndown.html` | SCA FindingLog burndown |
| `04-sast-burndown.html` | SAST / AI-SAST / Secrets FindingLog burndown |
| `data/packet.cube.json` | Portable cube (`endor.report_packet.v0`) |
| `README.txt` | Metric definitions for handoff |

## Endor Patches vs the product dashboard

The packet is **not** the live Patches UI. Quote the filter before comparing
counts. Guide: [docs/guides/executive-report-packet.md](../../../docs/guides/executive-report-packet.md).

| Surface | What it counts |
| -------- | -------------- |
| Packet pull | Critical + High, not dismissed, main context, **any reachability**, patch/fix gate |
| Packet **Available** catalog | `spec.fixing_patch.endor_patch_available==true` |
| Product Patches **Available** header | Same as catalog, but reach is RF **or** PRF only |
| Family / version group key | Vulnerable library current version: `spec.target_dependency_package_name` + `spec.target_dependency_version` |
| Not a group key | `spec.fixing_upgrades.upgrade_list` (upgrade-impact / what to bump) |

CSV `reachable` is RF-only. Use `reachable_function` /
`potentially_reachable_function`.

### Onboarding cadence (`reports.onboarding.cadence`)

- `weeklyMainFull` / `weeklyMainWithAnalytics` — estate MAIN weekly ScanResult counts (~90d).
- `weeklyCi` / CI project ranks use ~30d retention (`ciLookbackDays`); CI is not plotted on the 90d weekly chart.
- `byProject` / `byTag` / `topProjects` / `topTags` — rank by MAIN full scans then CI.
- UI: project-tag filter scopes registration, hierarchy, **scan-count tiles**, and ranks; **Exclude analytics** (on by default) opts out of `TYPE_ANALYTICS` / `TYPE_ANALYTICS_CHECK` on the MAIN weekly series; weekly chart stays org-wide.

## Metric captions (must preserve)

- Primary burndown stat: **Window net (CREATE−DELETE)** (may be negative; not open inventory).
- MAIN throughput: **Main-context scans (activity proxy)**.
- Tags without FindingLog series: **Trend charts not loaded for this tag yet…**
- Onboarding cadence default excludes `TYPE_ANALYTICS` / `TYPE_ANALYTICS_CHECK`.

## Library

```python
from endorlabs import Client
from endorlabs.workflows.reports import build_report_packet, render_report_packet

client = Client(tenant="<tenant>")
cube = build_report_packet(client, "<tenant>")
render_report_packet(cube, "path/to/out")
```

Use placeholders only in tracked examples (`example-tenant`, `<tenant>`).
