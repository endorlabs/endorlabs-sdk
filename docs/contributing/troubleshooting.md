# SDK troubleshooting (contributing)

Contributor workflow for validating SDK behavior against `endorctl`, contracts,
and integration tests. Shipped agent playbook:
[endor-troubleshoot-sdk](../../agent-knowledge/skills/endor-troubleshoot-sdk/SKILL.md)
and [validation-reference.md](../../agent-knowledge/skills/endor-troubleshoot-sdk/validation-reference.md).

Resolved-case narratives: local docs under `.endorlabs-context/platform/user-docs/` and repo issues.

## Platform insight: path namespace vs body UUID

For endpoints that take a **resource UUID in the body** and a **namespace in the path** (e.g. create scan-log-request with `scan_result_uuid`), the path namespace must be the **owning** namespace of that resource (the resource’s `tenant_meta.namespace`). Using a **parent** namespace may error even with a valid UUID. Validate with `endorctl` using the owning namespace from the resource row.

**Avoiding 404 after traverse:** When you act on objects returned from `list(traverse=True)` (or broad filters), pass the **resource object** to `get`, `update`, or `delete` (e.g. `client.Project.delete(target)`). The SDK then uses the resource's `tenant_meta.namespace` so the path matches the owning namespace; otherwise using the client default namespace can cause 404 Not Found. See [contracts.md](../contracts.md) (Namespace scoping) and `endorlabs.utils.resolve_namespace_for_resource`.

## Workflow

1. **Document** — Task, context, approach, errors and stack traces.
2. **Research** — Search codebase and docs; review API spec (see [contracts.md](../contracts.md)).
3. **Investigate** — Replay with `endorctl` using the same resource, namespace, filter, and traverse; classify using [validation-reference.md](../../agent-knowledge/skills/endor-troubleshoot-sdk/validation-reference.md).
4. **Resolve** — Implement fix; document signatures and learnings.

## Slow or hanging list operations

- **Narrow scope** first: list from a **child namespace** without `traverse` before using tenant-wide `traverse=True`.
- **Tighten `filter`** when the resource supports selective filters; avoid broad unfiltered lists on large tenants when possible.
- **Compare with `endorctl`** for the same resource, namespace, filter, and traverse to isolate client vs backend latency.
- **`max_pages`/`page_size`:** Capping pages bounds the client loop; it does not guarantee cheap server-side work for the first page. See [list-query-performance.md](list-query-performance.md).

## List ServerError at broad namespace scope

- Some resource kinds may error when listing at tenant root. The SDK surfaces backend errors as `ServerError`.
- **Interpretation**: If `endorctl` shows the same failure, treat as scope/platform behavior and retry at a child namespace. If `endorctl` returns **200** but SDK deserialization fails, treat as **model-sync drift** (**endor-model-sync-drift**).

### List mask vs partial **model** responses

- **Non-empty list field mask** (`mask=` / `ListParameters.mask`, non-empty after strip): `list()` / `list_iter()` return **wire JSON dicts** (or iterate dicts), not sparse Pydantic instances—there is no client-side “partial model” parse for those rows. Use dict access (or omit `mask` when you need full models).
- **No effective mask** (mask omitted, empty, or whitespace-only): list responses are still full resource models. At some scopes (e.g. tenant root) the API may omit fields the OpenAPI full schema marks as required; the SDK applies spec-aligned **leniency** when constructing models: **Finding** `context` may be omitted; **Project** `spec.platform_source` may be omitted when the response omits it; **BaseMeta** `name` may be omitted when the response omits it. Callers should still handle `None` for those attributes on **model** instances.

## Tenant-accessed resources (authentication_log, endor_license, policy_template)

`authentication_log`, `endor_license`, and `policy_template` are customer-accessible through tenant context. Use tenant clients and `traverse=True` where broad visibility is needed. `create`, `update`, and `delete` are not exposed on these facades.

## Test skips (short test summary)

When pytest reports skips (403, "No resources in scope", validation errors on update, semgrep "unexpected token null"): run `endorctl api list -r <Resource> --traverse -n <namespace>` (PascalCase for resource, e.g. `Finding`, `Project`) to validate whether the namespace has data; see endorctl docs for options (e.g. `--page-size`, `-o table`). **Warnings:** Run pytest without `--disable-warnings` to see whether the source is pytest, a library, or the SDK.

## Test resource cleanup (CREATE tests)

Every test that **creates** an API resource (and whose resource supports delete) must clean up in the **same test** using try/finally so cleanup runs on pass, assert failure, or exception. `teardown_method` remains as a backup.

See [integration-resource-tests.md](integration-resource-tests.md) for canonical test order, pagination profiles, and cleanup patterns.

**Verifying with endorctl:** To check for leftover test resources in a namespace (e.g. after interrupted runs), use the same namespace as tests (`ENDOR_NAMESPACE` or default `auri`):

- `endorctl api list -r APIKey -n <namespace> --traverse` — API keys (filter by name pattern in output if needed).
- `endorctl api list -r ScanProfile -n <root> --traverse` — scan profiles (tests create at root).
- `endorctl api list -r Namespace -n <namespace> --traverse` — child namespaces.
- `endorctl api list -r Policy -n <root> --traverse -f "meta.tags in ['test','crud-test']"` — test-tagged policies.
- `endorctl api list -r SemgrepRule -n <namespace> --traverse` — semgrep rules.
- `endorctl api list -r AuthorizationPolicy -n <namespace> --traverse` — authorization policies.

**Cleanup guidance:** When cleaning up leftover test resources, delete **only** resources matching strict test name/pattern criteria so legitimate policies and other stable entities are never targeted. For **policies**, both a test tag and a test-only name pattern are required (e.g. name starts with `Test Exception Policy `, `Test Notification Policy `, `Test Admission Policy `, `ClientUX Exception `, or `ClientUX Del `). For **other resources** (ApiKey, ScanProfile, Namespace, SemgrepRule, AuthorizationPolicy), only **name prefix or exact name** is used (no tag). Use the endorctl commands above to list matching resources, then delete individually via `endorctl api delete`.

## References

- OpenAPI/spec path and list/update patterns: [contracts.md](../contracts.md).
- Agent validation playbook: [validation-reference.md](../../agent-knowledge/skills/endor-troubleshoot-sdk/validation-reference.md).
- For resolved-case narratives (wrong URL pattern, update_mask, tags): use local docs snapshots under `.endorlabs-context/platform/user-docs/` or repo issues.
