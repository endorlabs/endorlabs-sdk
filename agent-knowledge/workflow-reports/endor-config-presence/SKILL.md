---
name: endor-config-presence
description: |
  Use when probing tenant or project onboarding configuration presence as a
  boolean / guided matrix (Installation, ScanProfile, AuthPolicy, license
  features, MAIN/CI scan activity, AI-SAST flags). Read-only. Not for executive
  onboarding growth charts, CLI vs Cloud CSV alone, GitHub org inventory, or
  mutating platform_setup creates.
---

# Onboarding config presence

Produce a **presence matrix** for “is this tenant/project onboarded enough to
operate?” Evidence-backed Tier A booleans, guided Tier B warns, and deferred
Tier C human topics.

## Scope

**In scope**

- Tenant-grain presence: Installation, ScanProfile (incl. default), AuthPolicy,
  IdentityProvider, NotificationTarget, license features, SystemConfig
  package-firewall section, **custom** Policy / SemgrepRule (excludes Endor Labs
  and 3rd-Party / platform-seeded rows).
- Project-grain presence: `is_app` / `is_cli` / `is_sbom`, scan profile
  association + AI-SAST / PR flags, MAIN full / CI scan activity, AI-SAST
  findings, latest scan execution, mixed registration/execution.
- Guided probes with “ask SE about …” hints.

**Out of scope**

- Executive onboarding cadence HTML → [endor-executive-report-packet](../endor-executive-report-packet/SKILL.md)
- CLI vs Cloud CSV inventory → [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md)
- GitHub App org selection / CI YAML / branch protection → Endor employee conversation (Tier C)
- Creating namespaces/installations/profiles → `platform_setup` (write path)

## CLI

```bash
uv run --env-file .env endor-config-presence -n <tenant> \
  --project <project-uuid> \
  --lookback-days 30
```

Default artifact:

`.endorlabs/tasks/<slug>-<YYYY-MM-DD>/onboarding_config_presence/presence_result.json`

## Library

```python
from endorlabs.workflows.platform import run_config_presence

result = run_config_presence(client, "<tenant>", project_uuid="<project-uuid>")
payload = result.to_dict()
```

## Related

- Catalog router: [endor-workflow-reports](../../skills/endor-workflow-reports/SKILL.md)
- Auth policy form heuristics: [endor-audit-authorization-policies](../endor-audit-authorization-policies/SKILL.md)
