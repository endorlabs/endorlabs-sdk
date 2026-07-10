---
name: endor-workflow-reports
description: 'Use when the user asks for tenant or namespace-level Endor Labs audit
  reports,

  CSV exports, Cursor canvases, or executive-style workflow summaries that are

  backed by bundled report scripts rather than day-0 SDK troubleshooting skills.

  Routes to auth, project inventory, CI version, finding trend, and PRF report

  playbooks. Not for single-project scan RCA, finding retrieval, SDK debugging,

  or policy validation.'
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

## Report catalog

| User asks for | Use report playbook | Default output |
| --- | --- | --- |
| Login counts by user, identity, or group | `workflow-reports/endor-auth-login-count/SKILL.md` | `.endorlabs-context/workspace/runs/auth-login-count/` |
| API key / credential expiry audit | `workflow-reports/endor-auth-credential-expiry/SKILL.md` | `.endorlabs-context/workspace/runs/auth-credential-expiry/` |
| AuthorizationPolicy claim / namespace form audit | `workflow-reports/endor-audit-authorization-policies/SKILL.md` | User-supplied CSV / JSON paths |
| CLI-scanned vs Cloud-integrated project classification | `workflow-reports/endor-cli-vs-cloud-projects/SKILL.md` | `.endorlabs-context/workspace/runs/cli-vs-cloud-projects/` |
| CI `endorctl` version inventory across latest CLI scans | `workflow-reports/endor-ci-endorctl-version-audit/SKILL.md` | `.endorlabs-context/workspace/runs/ci-endorctl-version-audit/` |
| Duplicate project registrations across namespaces | `workflow-reports/endor-duplicate-projects/SKILL.md` | `.endorlabs-context/workspace/runs/duplicate-projects/` |
| New vs resolved findings trend chart | `workflow-reports/endor-chart-new-vs-resolved-findings/SKILL.md` | `.endorlabs-context/workspace/runs/finding-log-weekly-trends/` |
| Potentially reachable finding approximation + PV resolution errors | `workflow-reports/endor-potentially-reachable-analysis/SKILL.md` | `.endorlabs-context/workspace/runs/potentially-reachable-analysis/` |

## Intake

Before running a report, identify:

- Target tenant or namespace.
- Whether child namespaces should be included (`traverse=True`) or a single
  namespace is intended.
- Date window, if the report is log or scan-history based.
- Desired artifact format: CSV, JSON, canvas, HTML, PDF, or chat summary only.
- Boundaries such as `max_pages`, project name filters, ecosystem filters, or
  “latest scan only”.
- Output directory under `.endorlabs-context/workspace/runs/<report-id>/`.

If the user does not specify a namespace, ask for it unless a safe default is
already established in the session.

## Workflow

1. Choose the matching report from the catalog table.
2. Read that report playbook before running commands; report playbooks contain
   specific filters, schemas, and artifact contracts.
3. Confirm credentials with the normal SDK auth path when needed (`endor-auth`
   or existing environment variables). Do not print secrets.
4. Run the available workflow entrypoint or repo script with placeholder-safe
   output paths under
   `.endorlabs-context/workspace/runs/<report-id>/`.
5. Summarize artifact paths, key counts, date windows, and any data gaps.
6. For canvas-generating reports, open or point to the generated `.canvas.tsx`
   only after confirming it was written.

## Output rules

- Keep generated artifacts under `.endorlabs-context/workspace/runs/`.
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
