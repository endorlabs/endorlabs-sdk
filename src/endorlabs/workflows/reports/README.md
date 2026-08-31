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
uv run endor-reports list                  # report picker (categories + default paths)
uv run endor-reports -n <tenant>                    # default build
uv run endor-reports build -n <tenant>
uv run endor-reports patches -n <tenant>
uv run endor-reports refresh-code --packet-dir <path>
uv run endor-reports parity -n <tenant> --baseline-adoption <path> ...
uv run endor-reports duplicates -n <tenant>
uv run endor-reports cli-vs-cloud -n <tenant>
uv run endor-reports login-count -n <tenant>
uv run endor-reports credential-expiry -n <tenant>
uv run endor-reports auth-policies -n <tenant>
uv run endor-reports ci-endorctl -n <tenant>
uv run endor-reports findings-trend -n <tenant>
uv run endor-reports prf-analysis -n <tenant>
uv run endor-reports package-resolution -n <tenant>
```

Deprecated (one release): `packet`, `upsert-code-findings`.

## Executive packet

Default build writes a browser-ready HTML set under
`.endorlabs/reports/<slug>-<YYYY-MM-DD>/`:

| Page | Content |
|------|---------|
| `01-onboarding.html` | Project registration + MAIN/CI scan cadence + tag/project ranks |
| `02-version-sprawl.html` | Dependency version sprawl |
| `03-sca-burndown.html` | SCA FindingLog burndown |
| `04-sast-burndown.html` | OpenGrep / AI-SAST / Secrets FindingLog burndown (license-gated) |
| `05-endor-patches.html` | Endor Patches impact (opt-in `--patches` + license-gated) |

Default full packet **omits** Patches (Finding list pull — slow on large
estates). Pass `--patches` to include, or `endor-reports patches -n <tenant>`
for a campaign batch that writes under
`.endorlabs/reports/patches/<slug>-<YYYY-MM-DD>/`
(override date with `--date-suffix 2026-08-28`). A patches-only run
emits only page 05 and the `patches-*.csv` exports.

Packet Available is any reachability; the product Patches dashboard header is
RF or PRF. Families group on the vulnerable library, not `upgrade_list`. See
[executive-report-packet.md](../../../../docs/guides/executive-report-packet.md#endor-patches-vs-the-product-dashboard).

When a slice is skipped in a full packet, its page renders an explicit callout
rather than empty charts — `_render_*` empty states in `export/html/render.py`.

Guide: [docs/guides/executive-report-packet.md](../../../../docs/guides/executive-report-packet.md).
Agent router: skill **endor-workflow-reports**.

## Findings burndown pull

Tag series: one FindingLog severity×reach matrix per **tagged** project
(parallel `--workers`, default 24), then local redistribute onto tags/paths.
Path series: leaf-namespace aggregates (includes untagged projects).
`--min-projects` only filters which tags appear in the packet (default 1).

Packet `data/` includes `packet.cube.json` plus CSV raw exports (gap
differentials, onboarding, throughput, tag catalog) — see `data/EXPORTS.txt`.

## Parity harness

`endorlabs.workflows.reports.parity` compares live packet cubes to gitignored
scratch baselines (paths from flags or `ENDOR_VALIDATE_*` env vars). Output:
`.endorlabs/tasks/parity/<slug>-<YYYY-MM-DD>/`.

Tolerances: onboarding ≤1%; sprawl/burndown aggregates ≤2%; throughput ≤5%;
`gapEnd` exact match.

## Portable content

Tracked code uses `example-tenant` / `<tenant>` only. Never commit customer
tenant names, project URLs, production UUIDs, or `.endorlabs/` outputs.

## Agent playbooks

Detailed report playbooks live in `agent-knowledge/workflow-reports/` (authoring
only — not shipped in the wheel). Router skill: **endor-workflow-reports**.
