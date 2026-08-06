# Executive report packet

Build a self-contained interactive HTML packet for a tenant or namespace:
organization onboarding (registration + scan/PR cadence), dependency version
sprawl, FindingLog burndown (SCA + SAST / AI-SAST / Secrets), and Endor Patches
impact.

Open the HTML files in any browser — no Cursor runtime required.

## Command

```bash
uv run --env-file .env endor-reports packet -n <tenant>
```

Privileged read against customer tenants: refresh SSO against `endor-admin`, then
pass the **customer** namespace only on `-n` (see skill **endor-auth-setup** /
employee auth notes).

Optional flags: `--lookback`, `--min-projects`, `--workers`, `--output-dir`,
`--log-level` (stdout stage milestones: `packet.discover.*`, burndowns, patches,
render; also `ENDOR_LOG_LEVEL`), `--skip-version-sprawl`,
`--skip-findings-burndown`, `--skip-patches`, `--patches-only` (Patches page only
→ `runs/patches-reports/<tenant>-MMDDYY/`).

`--patches-only` writes just `05-endor-patches.html` and the `patches-*.csv`
exports — pages 01–04 are omitted rather than rendered from slices the run never
collected.

Slice failures (for example FindingLog read timeouts on SCA burndown) no longer
abort the whole packet: other pages still write under the output dir, the cube
records `dataGaps` / `reportsMeta`, and the CLI exits `1` so operators notice.
Leaf FindingLog aggregates escalate to per-project shards on timeout.

## Outputs

Default directory:
`.endorlabs-context/workspace/runs/executive-report-packet/`.

| File | Content |
|------|---------|
| `01-onboarding.html` | Project registration + MAIN/CI scan cadence + tag/project ranks |
| `02-version-sprawl.html` | Dependency version sprawl |
| `03-sca-burndown.html` | SCA FindingLog burndown |
| `04-sast-burndown.html` | SAST / AI-SAST / Secrets FindingLog burndown |
| `05-endor-patches.html` | Endor Patches impact (Available / To Request) |
| `data/packet.cube.json` | Portable cube (`endor.report_packet.v0`) |
| `data/*.csv` | Raw exports (see `data/EXPORTS.txt`) |

## Agent routing

Skill **endor-workflow-reports** → playbook
`endor-executive-report-packet` (authoring tree; catalog id
`executive-report-packet`).

## Library

```python
from endorlabs import Client
from endorlabs.workflows.reports import build_report_packet, render_report_packet

client = Client(tenant="<tenant>")
cube = build_report_packet(client, "<tenant>")
render_report_packet(cube, "path/to/out")
```

Maintainer layout: [src/endorlabs/workflows/reports/README.md](../../src/endorlabs/workflows/reports/README.md).
