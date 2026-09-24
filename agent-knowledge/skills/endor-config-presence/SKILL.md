---
name: endor-config-presence
description: |
  Use when probing tenant or project onboarding configuration presence as a
  boolean / guided matrix (Installation, ScanProfile, AuthPolicy, license
  features, MAIN/CI scan activity). Aggregates checks into a default bucket
  (auth/SSO/policies/…) plus feature-specific license buckets. Read-only
  quick status. Not for executive onboarding growth charts, CLI vs Cloud CSV
  inventory, GitHub org inventory, or mutating platform_setup creates.
endorlabs:
  catalog:
    workflow_id: config-presence
    module: endorlabs.workflows.platform.cli
    cli: endor-config-presence
    default_output: .endorlabs/tasks/<slug>-<YYYY-MM-DD>/onboarding_config_presence/
    agent_visible: true
    composition: library_api
    library_entrypoints:
      - endorlabs.workflows.platform.config_presence.run_config_presence
      - endorlabs.workflows.platform.config_presence.probe_tenant_presence
      - endorlabs.workflows.platform.config_presence.probe_project_presence
---

# Onboarding config presence

Produce a **presence matrix** for “is this tenant/project onboarded enough to
operate?” Evidence-backed Tier A booleans, guided Tier B warns, and deferred
Tier C human topics.

## Scope

**In scope**

- Tenant-grain presence: Installation, ScanProfile (incl. default), AuthPolicy,
  IdentityProvider, NotificationTarget, custom Policy, custom SemgrepRule,
  SystemConfig package-firewall, license entitlement rows.
- Project-grain presence: `is_app` / `is_cli` / `is_sbom`, scan profile
  association + AI-SAST / PR flags, MAIN full / CI scan activity, AI-SAST
  findings / vector rows.
- **License aggregation** (`by_license` in the artifact): `default` holds
  auth/SSO/policies/install/profile/cadence and any unmapped check; feature
  buckets (SAST, AI-SAST, Package Firewall, …) group entitlement + related
  config like-by-like. Checks always run; `entitled` on each bucket reflects
  the license, it does not skip probes.
- Guided probes with “ask SE about …” hints.

**Out of scope**

- Executive onboarding cadence HTML / tenant audit CSVs → [endor-workflow-reports](../endor-workflow-reports/SKILL.md)
- GitHub App org selection / CI YAML / branch protection → Endor employee conversation (Tier C)
- Creating namespaces/installations/profiles → `platform_setup` (write path)
- Auth credential probe/refresh → [endor-auth-setup](../endor-auth-setup/SKILL.md)

## CLI

```bash
uv run --env-file .env endor-config-presence -n <tenant> \
  --project <project-uuid> \
  --lookback-days 30
```

Default artifact:

`.endorlabs/tasks/<slug>-<YYYY-MM-DD>/onboarding_config_presence/presence_result.json`

Exit `0` only when overall status is `success` (warns allowed); `partial` / `error` → exit `1`.

## Library

```python
from endorlabs.workflows.platform import run_config_presence

result = run_config_presence(client, "<tenant>", project_uuid="<project-uuid>")
payload = result.to_dict()
# payload["by_license"]["default"] — auth / SSO / policies / …
# payload["by_license"]["ENDOR_LICENSE_FEATURE_TYPE_SAST"] — entitlement + Semgrep
```

## Related skills

| Need | Skill |
|------|-------|
| Tenant audit CSVs / executive packet | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) |
| AuthPolicy form heuristics deep-dive | [endor-workflow-reports](../endor-workflow-reports/SKILL.md) (`auth-policies`) |
| Credential probe / refresh | [endor-auth-setup](../endor-auth-setup/SKILL.md) |
| SBOM import / Project.is_sbom follow-up | [endor-sbom-management](../endor-sbom-management/SKILL.md) |
| SSO claim mapping RCA | [endor-troubleshoot-authlog](../endor-troubleshoot-authlog/SKILL.md) |
