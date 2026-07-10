# Workflow report playbooks (not shipped individually)

Detailed report playbooks and scripts live here. The shipped discovery entrypoint
is `agent-knowledge/skills/endor-workflow-reports/SKILL.md`; keep these report
directories out of `src/endorlabs/agent_knowledge/skills/` as individual skills.

These workflows generate tenant/namespace reports (CSV, JSON, Cursor canvas,
HTML, or PDF). They are script-backed report routines, not day-0 SDK RCA
playbooks.

| Id | Scripts / module |
| --- | --- |
| `endor-auth-login-count` | `scripts/login_count_report.py` · `endorlabs.workflows.auth` |
| `endor-auth-credential-expiry` | `scripts/credential_expiry_report.py` · `endorlabs.workflows.auth` |
| `endor-audit-authorization-policies` | `scripts/audit_authorization_policies.py` |
| `endor-cli-vs-cloud-projects` | `scripts/classify_cli_vs_cloud_projects.py` |
| `endor-ci-endorctl-version-audit` | `scripts/audit_ci_endorctl_versions.py` |
| `endor-duplicate-projects` | `scripts/find_duplicate_projects.py` |
| `endor-chart-new-vs-resolved-findings` | `scripts/` · `finding_log_trends` |
| `endor-potentially-reachable-analysis` | `scripts/` · PRF analysis |

Library-backed report workflow rows live in `agent-knowledge/workflows.yaml`
with `skill: endor-workflow-reports` and `agent_visible: false`; detailed
playbooks remain here instead of shipping as independent skills.
