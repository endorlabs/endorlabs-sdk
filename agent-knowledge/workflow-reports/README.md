# Workflow report playbooks (not shipped individually)

Detailed report playbooks live here. The shipped discovery entrypoint
is `agent-knowledge/skills/endor-workflow-reports/SKILL.md`; keep these report
directories out of `src/endorlabs/agent_knowledge/skills/` as individual skills.

Report logic ships in the wheel under `endorlabs.workflows.reports` and is
invoked via **`endor-reports <subcommand>`** (see
`src/endorlabs/workflows/reports/README.md`).

| Id | CLI subcommand | SDK module |
| --- | --- | --- |
| `endor-auth-login-count` | `login-count` | `reports.analyze.auth_login_count` |
| `endor-auth-credential-expiry` | `credential-expiry` | `reports.analyze.auth_credential_expiry` |
| `endor-audit-authorization-policies` | `auth-policies` | `reports.analyze.auth_policies_audit` |
| `endor-cli-vs-cloud-projects` | `cli-vs-cloud` | `reports.analyze.cli_vs_cloud` |
| `endor-ci-endorctl-version-audit` | `ci-endorctl` | `reports.analyze.ci_endorctl_audit` |
| `endor-duplicate-projects` | `duplicates` | `reports.analyze.duplicate_projects` |
| `endor-chart-new-vs-resolved-findings` | `findings-trend` | `reports.analyze.findings_chart_analysis` |
| `endor-executive-report-packet` | `packet` / `parity` | `reports.bundles.executive_packet` |
| `endor-potentially-reachable-analysis` | `prf-analysis` | `reports.analyze.prf_report_analysis` |

Library-backed report workflow rows live in `agent-knowledge/workflows.yaml`
with `skill: endor-workflow-reports` and `agent_visible: false`; detailed
playbooks remain here instead of shipping as independent skills.
