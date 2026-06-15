# PolicyValidation API reference

Operation: **`PolicyValidationService_CreatePolicyValidation`**

```
POST {BASE_URL}/v1/namespaces/{NAMESPACE}/policy/validate
Authorization: Bearer {TOKEN}
Content-Type: application/json
```

Only **POST** is supported (other verbs return 501).

## Request body

Always include **`tenant_meta.namespace`** matching the URL path.

### Templated policy (preferred when policy has `spec.template_uuid`)

```json
{
  "tenant_meta": { "namespace": "customer.namespace" },
  "meta": { "name": "policy-validation-request" },
  "spec": {
    "request": {
      "policy_type": "POLICY_TYPE_EXCEPTION",
      "template_uuid": "<TEMPLATE_UUID>",
      "template_values": {
        "VulnID": { "values": ["CVE-2026-42033"] },
        "MatchApproximate": { "values": ["Yes"] },
        "FixAvailability": {},
        "Relationship": {},
        "Scope": {},
        "Severity": {}
      },
      "project_uuid": "<PROJECT_UUID>",
      "disable_preview": false
    }
  }
}
```

If not using `template_uuid`, send **`rule`**, **`query_statements`**, and **`resource_kinds`** directly in `spec.request` (copy from stored policy `spec`).

### Preview-only (no project data)

Set `"disable_preview": true` and omit `project_uuid`.

## Response (`v1PolicyValidation`)

```json
{
  "tenant_meta": { "namespace": "..." },
  "meta": { "name": "policy-validation-request" },
  "spec": {
    "result": {
      "valid_policy": true,
      "validation_error": "",
      "allow": null,
      "policy_rule": "...",
      "query_statements": ["data.vulnerabilities.match_finding"],
      "resource_kinds": ["Finding"],
      "policy_output": {
        "<project_uuid>": {
          "violating_resources": { "...": { "uuids": ["..."] } },
          "allow": false
        }
      },
      "evaluation_time": { "<project_uuid>": "1234" }
    }
  }
}
```

| Field | Meaning |
|-------|---------|
| `valid_policy` | Rego valid and evaluation completed |
| `validation_error` | Set when `valid_policy` is false |
| `policy_output` | Matches keyed by project UUID |
| `allow` | Policy accept/reject for input data (may be null on exceptions) |

## curl example

```bash
curl -sS -X POST "https://api.endorlabs.com/v1/namespaces/customer.namespace/policy/validate" \
  -H "Authorization: Bearer ${ENDOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_meta": { "namespace": "customer.namespace" },
    "meta": { "name": "policy-validation-request" },
    "spec": {
      "request": {
        "policy_type": "POLICY_TYPE_EXCEPTION",
        "template_uuid": "6839f54bfc0b87f4c01f2d83",
        "template_values": {
          "VulnID": { "values": ["CVE-2026-42033"] }
        },
        "project_uuid": "<PROJECT_UUID>",
        "disable_preview": false
      }
    }
  }'
```

## SDK helper

`build_validation_body()` in `endorlabs.workflows.policies.validate` builds this payload from a loaded `Policy` model.
