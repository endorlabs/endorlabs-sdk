# endorctl parity

`endorctl validate policy` is the product CLI for the same **business question**: which
findings match this policy for this project?

## Command

```bash
endorctl validate policy \
  --policy-uuid <POLICY_UUID> \
  --uuid <PROJECT_UUID> \
  --namespace <NAMESPACE> \
  --output-type json \
  --bypass-host-check
```

| Flag | Maps to API `spec.request` |
|------|------------------------------|
| `--namespace` | URL `/v1/namespaces/{ns}/…` |
| `--policy-uuid` | Server loads policy (template or rule) |
| `--uuid` | `project_uuid` |
| `-i` / `--input` | Extra template parameter JSON file |
| `-p` + `-q` + `-r` | Local Rego file path (rule + query + resource kinds) |

## Implementation difference

At `--log-level debug`, endorctl:

1. Lists findings via `dbloader` (standard list APIs)
2. Evaluates Rego locally in `policymgr`

It does **not** POST to `/policy/validate`. Therefore:

- endorctl can succeed when SDK `policy/validate` returns **403** (different auth surface)
- Output shape differs: endorctl JSON has **`matching_findings`** array; API uses **`spec.result.policy_output`**

## Exit codes (endorctl)

| Code | Meaning |
|------|---------|
| 0 | Valid policy, no matches |
| 128 | Valid policy, one or more matches |
| 18 | Policy evaluation error |

See `.endorlabs-context/docs/developers-api/cli/commands/validate/policy.md`.
