# Executive report packet

Build a self-contained interactive HTML packet for a tenant or namespace:
organization onboarding (registration + scan/PR cadence), dependency version
sprawl, and FindingLog burndown (SCA + SAST / AI-SAST / Secrets).

Open the HTML files in any browser — no Cursor runtime required.

## Command

```bash
uv run --env-file .env endor-reports packet -n <tenant>
```

Privileged read against customer tenants: refresh SSO against `endor-admin`, then
pass the **customer** namespace only on `-n` (see skill **endor-auth-setup** /
employee auth notes).

Optional flags: `--lookback`, `--min-projects`, `--workers`, `--output-dir`,
`--skip-version-sprawl`, `--skip-findings-burndown`.

## Outputs

Default directory:
`.endorlabs-context/workspace/runs/executive-report-packet/`.

| File | Content |
|------|---------|
| `01-onboarding.html` | Project registration + MAIN/CI scan cadence + tag/project ranks |
| `02-version-sprawl.html` | Dependency version sprawl |
| `03-sca-burndown.html` | SCA FindingLog burndown |
| `04-sast-burndown.html` | SAST / AI-SAST / Secrets FindingLog burndown |
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
