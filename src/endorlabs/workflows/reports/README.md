# Reports workflows

Tenant and namespace report workflows under `endorlabs.workflows.reports`:
**analyze** → **export** → **bundles**, with a single CLI (`endor-reports`).

## Layout

| Region | Role |
|--------|------|
| `analyze/` | `Client` in → structured dict (no file I/O) |
| `export/html/` | Executive packet HTML render + copy |
| `export/csv/` | Tabular CSV writers (report-specific) |
| `export/canvas/` | Cursor canvas / PDF orchestration |
| `schemas/` | `endor.report_packet.v0` and tabular contracts |
| `bundles/` | Multi-report deliverables (`executive_packet`) |
| `parity.py` | Compare packet cube to scratch baseline JSON (no tenant literals) |
| `cli.py` | All `endor-reports` subcommands |
| `packet/` | **Deprecated** one-release shims → new modules |

## CLI subcommands

```bash
uv run endor-reports packet -n <tenant>
uv run endor-reports parity -n <tenant> --baseline-adoption <path> ...
uv run endor-reports duplicates -n <tenant>
uv run endor-reports cli-vs-cloud -n <tenant>
uv run endor-reports login-count -n <tenant>
uv run endor-reports credential-expiry -n <tenant>
uv run endor-reports auth-policies -n <tenant>
uv run endor-reports ci-endorctl -n <tenant>
uv run endor-reports findings-trend -n <tenant>
uv run endor-reports prf-analysis -n <tenant>
```

## Findings burndown pull

Tag series: one FindingLog severity×reach matrix per **tagged** project
(parallel `--workers`, default 24), then local redistribute onto tags/paths.
Path series: leaf-namespace aggregates (includes untagged projects).
`--min-projects` only filters which tags appear in the packet (default 1).

## Parity harness

`endorlabs.workflows.reports.parity` compares live packet cubes to gitignored
scratch baselines (paths from flags or `ENDOR_VALIDATE_*` env vars). Output:
`.endorlabs-context/workspace/runs/report-parity/<tenant>-<YYYYMMDD>/`.

Tolerances: onboarding ≤1%; sprawl/burndown aggregates ≤2%; throughput ≤5%;
`gapEnd` exact match.

## Portable content

Tracked code uses `example-tenant` / `<tenant>` only. Never commit customer
tenant names, project URLs, production UUIDs, or `.endorlabs-context/` outputs.

## Agent playbooks

Detailed report playbooks live in `agent-knowledge/workflow-reports/` (authoring
only — not shipped in the wheel). Router skill: **endor-workflow-reports**.
