---
name: endor-executive-report-packet
description: |
  Use when producing a tenant-level executive interactive HTML report packet
  (onboarding, dependency version sprawl, vulnerability FindingLog trends) for
  browser handoff. Not for single-project RCA, estate IR collect, or Cursor
  canvas-only artifacts.
endorlabs:
  catalog:
    workflow_id: executive-report-packet
    module: endorlabs.workflows.reports.cli
    agent_visible: false
    library_entrypoints:
      - endorlabs.workflows.reports.bundles.executive_packet.build_report_packet
      - endorlabs.workflows.reports.export.html.render.render_report_packet
      - endorlabs.workflows.reports.parity.compare_packet_cube
---

# Executive report packet

Build a **self-contained HTML packet** for a tenant or namespace: organization
onboarding, dependency version sprawl, and vulnerability findings trend
(FindingLog CREATE/DELETE). Open the HTML files in any browser — no Cursor
runtime required.

## Scope

**In scope**

- Tenant/namespace executive HTML under
  `.endorlabs-context/workspace/runs/executive-report-packet/`.
- Project tag discovery from `Project.meta.tags` (full catalog; no allowlists).
- FindingLog window-net trends with cost-controlled tag series (`--min-projects`).

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
- `--min-projects 5` — minimum projects for tag FindingLog series
- `--output-dir <path>` — override default runs bucket
- `--skip-version-sprawl` / `--skip-findings-burndown` — partial packets

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
| `01-onboarding.html` | Organization onboarding |
| `02-version-sprawl.html` | Dependency version sprawl |
| `03-findings-burndown.html` | Vulnerability findings trend |
| `data/packet.cube.json` | Portable cube (`endor.report_packet.v0`) |
| `README.txt` | Metric definitions for handoff |

## Metric captions (must preserve)

- Primary burndown stat: **Window net (CREATE−DELETE)** (may be negative; not open inventory).
- MAIN throughput: **Main-context scans (activity proxy)**.
- Tags without FindingLog series: **Trend charts not loaded for this tag yet…**

## Library

```python
from endorlabs import Client
from endorlabs.workflows.reports import build_report_packet, render_report_packet

client = Client(tenant="<tenant>")
cube = build_report_packet(client, "<tenant>")
render_report_packet(cube, "path/to/out")
```

Use placeholders only in tracked examples (`example-tenant`, `<tenant>`).
