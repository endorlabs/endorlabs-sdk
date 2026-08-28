---
name: endor-workflow-reports
description: |
  Use when the user asks for tenant or namespace-level Endor Labs audit reports,
  CSV exports, Cursor canvases, executive HTML report packets (QBR / customer)
  read-out / org onboarding growth / dependency sprawl / SCA·SAST·Secrets
  FindingLog burndown), PackageVersion resolution HTML, or workflow summaries
  backed by bundled report scripts rather than day-0 SDK troubleshooting skills.
  Routes to auth, project inventory, CI version, finding trend, executive HTML
  packet, package-resolution, and PRF report playbooks. Not for single-project
  scan RCA, finding retrieval, SDK debugging, or policy validation.
---

# Workflow reports

Route requests for scripted Endor Labs report generation. This skill is a
catalog/router: use it to choose the right report workflow. In the SDK repo,
detailed playbooks live under `agent-knowledge/workflow-reports/<id>/`; in an
installed bootstrap bundle, use this catalog and the manifest workflow rows
because detailed report playbooks are not shipped individually.

These workflows are intentionally not individual discovery skills. They are
tenant/namespace report generators with CSV, JSON, canvas, HTML, or PDF outputs;
shipping each one as a top-level skill would add discovery noise for normal SDK
RCA tasks.

## Scope

Use this skill for:

- Tenant or namespace-wide audit reports.
- CSV exports intended for review or customer handoff.
- Cursor canvas reports generated from saved analysis JSON.
- Scheduled or ad-hoc summary reports over projects, auth logs, scan metadata,
  finding logs, or PackageVersion resolution evidence.

Do not use this skill for:

- Single-project findings or latest scan retrieval → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- Scan failure or metrics RCA → [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md)
- SDK/API errors or model drift → [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md)
- PolicyValidation or exception policy matching → [endor-validate-policy](../endor-validate-policy/SKILL.md)

## When to recommend the executive HTML build

Prefer the executive HTML packet when the user asks for any of:

- A **customer / QBR / executive read-out** they can open in a browser (self-contained HTML).
- **Organization onboarding / project growth** over time, including scan and PR cadence.
- **Dependency version sprawl** across the tenant or project tags.
- **FindingLog burndown** for SCA (reachability) and/or SAST / AI-SAST / Secrets.
- **Endor Patches** impact (Available / To Request) for a campaign read-out.

Command: `uv run --env-file .env endor-reports -n <tenant>` (default **build**)
Output: `.endorlabs/reports/<slug>-<YYYY-MM-DD>/`
Include Patches: add `--patches`. Campaign-only:
`endor-reports patches -n <tenant>`
→ `.endorlabs/reports/patches/<slug>-<YYYY-MM-DD>/`
Refresh SAST burndown only into an existing packet:
`endor-reports refresh-code --packet-dir <path>`

Deprecated (one release): `endor-reports packet` and `endor-reports upsert-code-findings`.
Playbook: `agent-knowledge/workflow-reports/endor-executive-report-packet/SKILL.md`.
Packet Available is any reachability (not the product RF|PRF header). Families
group on the vulnerable library (`target_dependency_*`), not `upgrade_list`.

## Report catalog

Run `uv run endor-reports list` (or `list --json`) for the full subcommand picker.
`-n` / `--namespace` placement is flexible; falls back to `ENDOR_NAMESPACE`.

| User asks for | CLI subcommand | Default output |
| --- | --- | --- |
| Login counts by user, identity, or group | `endor-reports login-count -n <tenant>` | `.endorlabs/reports/auth-login-count/` |
| API key / credential expiry audit | `endor-reports credential-expiry -n <tenant>` | `.endorlabs/reports/auth-credential-expiry/` |
| AuthorizationPolicy claim / namespace form audit | `endor-reports auth-policies -n <tenant>` | `.endorlabs/reports/auth-policies/` |
| CLI-scanned vs Cloud-integrated project classification | `endor-reports cli-vs-cloud -n <tenant>` | `.endorlabs/reports/cli-vs-cloud/` |
| CI `endorctl` version inventory across latest CLI scans | `endor-reports ci-endorctl -n <tenant>` | `.endorlabs/reports/ci-endorctl/` |
| Duplicate project registrations across namespaces | `endor-reports duplicates -n <tenant>` | `.endorlabs/reports/duplicates/` |
| New vs resolved findings trend chart | `endor-reports findings-trend -n <tenant>` | `.endorlabs/reports/findings-trend/` |
| Executive interactive HTML packet (onboarding + scan/PR cadence, sprawl, SCA + SAST/Secrets FindingLog burndown; add `--patches` for Endor Patches) | `endor-reports -n <tenant>` or `endor-reports build -n <tenant>` | `.endorlabs/reports/<slug>-<YYYY-MM-DD>/` |
| Endor Patches campaign page only | `endor-reports patches -n <tenant>` | `.endorlabs/reports/patches/<slug>-<YYYY-MM-DD>/` |
| Refresh SAST/AI-SAST/Secrets burndown in existing packet | `endor-reports refresh-code --packet-dir <path>` | In-place under `--packet-dir` |
| Potentially reachable finding approximation + PV resolution errors | `endor-reports prf-analysis -n <tenant>` | `.endorlabs/reports/prf-analysis/` |
| PackageVersion resolution CSV + interactive HTML (manifest / dep resolution / reachability) | `endor-reports package-resolution -n <tenant>` | `.endorlabs/reports/package-resolution/` |

Playbooks (filters, schemas, edge cases): `agent-knowledge/workflow-reports/<id>/SKILL.md`.

## Intake

Before running a report, identify:

- Target tenant or namespace.
- Whether child namespaces should be included (`traverse=True`) or a single
  namespace is intended.
- Date window, if the report is log or scan-history based.
- Desired artifact format: CSV, JSON, canvas, HTML, PDF, or chat summary only.
- Boundaries such as `max_pages`, project name filters, ecosystem filters, or
  “latest scan only”.
- Output directory under `.endorlabs/reports/<report-id>/`.

If the user does not specify a namespace, ask for it unless a safe default is
already established in the session.

## Workflow

1. Choose the matching report from the catalog table.
2. Read that report playbook before running commands; report playbooks contain
   specific filters, schemas, and artifact contracts.
3. Confirm credentials with the normal SDK auth path when needed (`endor-auth`
   or existing environment variables). Do not print secrets.
4. Run the matching `endor-reports <subcommand>` with placeholder-safe
   output paths under
   `.endorlabs/reports/<report-id>/`.
5. Summarize artifact paths, key counts, date windows, and any data gaps.
6. For canvas-generating reports, open or point to the generated `.canvas.tsx`
   only after confirming it was written.

## Output rules

- Keep generated artifacts under `.endorlabs/reports/`.
- Use stable filenames containing the namespace or tenant slug and report id.
- Do not commit generated CSV, JSON, HTML, PDF, or canvas artifacts.
- Do not invent missing rows; report `data_gaps` when API calls are unavailable,
  truncated, unauthenticated, or out of scope.
- Prefer rerendering from existing analysis JSON when the user only asks to
  refresh a canvas/PDF and inputs have not changed.

## Workflow catalog linkage

Workflow rows for library-backed report routines live in
`agent-knowledge/workflows.yaml` with `skill: endor-workflow-reports` and
`agent_visible: false` so they route through this skill without appearing as
independent workflow entries.

Keep detailed report playbooks under `agent-knowledge/workflow-reports/` and do
not sync that tree directly into `src/endorlabs/agent_knowledge/skills/`.
