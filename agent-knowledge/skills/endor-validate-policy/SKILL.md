---
name: endor-validate-policy
description: >-
  Validate Endor Labs policies against project finding data via the
  PolicyValidation API or endorctl. Use when checking whether an exception
  policy matches a finding, debugging VulnID/template_values, comparing SDK
  POST policy/validate to endorctl validate policy, or triaging 403 authz on
  customer namespaces.
endorlabs:
  catalog:
    workflow_id: policies-validate
    module: endorlabs.workflows.policies.validate
    default_output: stdout or --output-json
    agent_visible: true
    composition: library_api
    library_entrypoints:
      - endorlabs.workflows.policies.run_validate_policy
---

# Validate Policy

Extend with [workflow-composition](../../rules/endor-workflow-composition.md): prefer `run_validate_policy` in session scripts instead of forking the CLI.

Evaluate whether a **stored policy** (usually an exception policy) matches
findings for a **project** — without applying exceptions in production.

## First principles

| Concept | Meaning |
|---------|---------|
| **Policy** | Rego rule + metadata; exception policies mark findings as false positive / risk accepted via `spec.exception`. |
| **Template policy** | Policy created from `PolicyTemplate`; criteria live in `spec.template_values` (e.g. `VulnID`, `MatchApproximate`). |
| **Rule-only policy** | Policy with inline `spec.rule` + `spec.query_statements` + `spec.resource_kinds` (no `template_uuid`). |
| **Validate** | Run the policy Rego against **loaded Finding rows** for a project; return matches (violating / matching findings). |
| **Preview (`disable_preview: true`)** | Check Rego/template **syntax and inputs only** — no project data loaded. |
| **Full evaluate (`disable_preview: false` + `project_uuid`)** | Load project findings and return matches — closest to `endorctl validate policy --uuid …`. |

**Validate is not the same as apply.** A match means the policy **would** except those findings under current scan data; it does not write exceptions until the policy runs in scan/CI flows.

## Two execution paths

| Path | When to use | Auth |
|------|-------------|-----|
| **SDK — `POST …/policy/validate`** | Automation, JSON in/out, tenant-scoped scripts | **Tenant credentials** for the **customer namespace** in the URL |
| **endorctl — `validate policy`** | Parity with product CLI, large match sets | Same tenant token; **does not call** `policy/validate` (lists findings + local Rego) |

See [policy-validation-api.md](policy-validation-api.md) for request/response shape and [policy-validation-endorctl.md](policy-validation-endorctl.md) for CLI parity.

## Requirements

### Credentials and namespace

1. **`ENDOR_NAMESPACE`** (or `--namespace`) must be the **customer tenant** you are validating (e.g. `<customer-namespace>`).
2. Include **`tenant_meta.namespace`** in the POST body with the **same** value as the URL path segment.
3. **Cross-tenant endor-admin read** against a **customer** namespace often returns **403** on `policy/validate` even when `Policy.get` / `Finding.list` succeed. Reproduce in your **home tenant** first, or use **tenant-scoped** user/service credentials for customer work.
4. Run with `uv run --env-file .env …`; refresh token via `uv run endor-auth refresh --method sso -n <tenant>` when needed.

### Inputs

| Input | Required | Source |
|-------|----------|--------|
| `policy_uuid` | Yes | UI or `client.Policy.list` |
| `project_uuid` | For full evaluate | `--uuid` in endorctl; `spec.project_uuid` on a finding |
| `finding_uuid` | Optional | Convenience: resolves `project_uuid`; check match in output |
| `template_uuid` + `template_values` | If policy is templated | Copied from stored policy `spec` |
| `rule` + `query_statements` + `resource_kinds` | If not templated | Copied from stored policy `spec` |

### Matching gotchas (SCA exception template `<TEMPLATE_UUID>`)

- **`VulnID`**: Rego matches `vulnerability.meta.name` **and** `vulnerability.spec.aliases` (exact, lowercased). Trim CVE/GHSA strings — leading spaces in template values **never match**.
- **`MatchApproximate: Yes`**: Requires `finding.spec.approximation == true`. Omit or leave empty to skip that gate.
- **`valid_policy: true`** with empty `policy_output` means syntax OK but **no matches** for the project — not an API failure.

## Workflow

### Step 1 — Resolve policy and project

```python
import endorlabs

client = endorlabs.Client(tenant="example-tenant.child")
policy = client.Policy.get("<policy-uuid>", namespace="example-tenant.child")

finding = client.Finding.get("<finding-uuid>", namespace="example-tenant.child")
project_uuid = finding.spec.project_uuid
```

### Step 2 — Call validate (SDK)

```bash
uv run --env-file .env python -m endorlabs.workflows.policies.validate \
  --namespace example-tenant.child \
  --policy-uuid <POLICY_UUID> \
  --finding-uuid <FINDING_UUID> \
  --output-json
```

Or programmatically:

```python
from endorlabs.workflows.policies import run_validate_policy

result = run_validate_policy(
    namespace="example-tenant.child",
    policy_uuid="<policy-uuid>",
    finding_uuid="<finding-uuid>",
)
print(result.finding_matched)
```

### Step 3 — Interpret response

- `spec.result.valid_policy` — Rego compiled and ran (`true` / `false`).
- `spec.result.validation_error` — compile/runtime error text when `valid_policy` is false.
- `spec.result.policy_output` — map keyed by **project UUID** → matching resource UUIDs.
- Compare a specific finding: `finding_matched` or search response JSON for finding UUID.

### Step 4 — endorctl parity (optional)

```bash
endorctl validate policy \
  --policy-uuid <POLICY_UUID> \
  --uuid <PROJECT_UUID> \
  --namespace example-tenant.child \
  --output-type json \
  --bypass-host-check
```

Output uses top-level `matching_findings` (full finding objects), not `spec.result.policy_output`.

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| **403** on `policy/validate` | Wrong credential class (admin cross-tenant) or wrong namespace in URL |
| **403** on customer namespace, **200** on home tenant | Authz on x-internal endpoint, not bad JSON |
| Policy should match finding but does not | `VulnID` typo/spacing; `MatchApproximate`; empty template param `{}` vs omitted |
| endorctl works, SDK 403 | endorctl uses list + local Rego, not `policy/validate` |
| **501** on PUT/PATCH/GET | Only **POST** is implemented on this route |

## References

- OpenAPI: `PolicyValidationService_CreatePolicyValidation` → `POST /v1/namespaces/{tenant_meta.namespace}/policy/validate` (`x-internal: true`)
- Product docs (validate policy CLI): Docs MCP → search “validate policy” / `developers-api/cli/commands/validate/policy` ([Docs MCP setup](https://docs.endorlabs.com/introduction/docs-mcp-server))
- Implementation: `src/endorlabs/workflows/policies/validate.py`
- Fixture probe (creates templated policy in `ENDOR_NAMESPACE`): place under `.endorlabs-context/workspace/runs/scratch/policy_validate_probe.py` (see [workspace-layout](../../rules/endor-workspace-layout.md))

Run validate:

```bash
uv run --env-file .env python -m endorlabs.workflows.policies.validate \
  --policy-uuid <POLICY_UUID> \
  --finding-uuid <FINDING_UUID>
```

## Related skills

| Need | Skill |
| ---- | ----- |
| Resolve finding UUID / project namespace | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| Scan pipeline or aggregate count regression | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Package/finding lineage at commit scope | [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) |
