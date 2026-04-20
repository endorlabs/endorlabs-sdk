# Troubleshooting Rules of Engagement

Workflow below. Resolved-case narratives: local docs snapshots under `.endorlabs-context/docs/` and repo issues.

## Platform insight: path namespace vs body UUID

For endpoints that take a **resource UUID in the body** and a **namespace in the path** (e.g. create scan-log-request with `scan_result_uuid`), the path namespace must be the **owning** namespace of that resource (the resource’s `tenant_meta.namespace`). Using a **parent** namespace can return 500 even with a valid UUID. This behavior is not always stated in the API spec; document it in SDK docstrings once confirmed.

**Avoiding 404 after traverse:** When you act on objects returned from `list(traverse=True)` (or broad filters), pass the **resource object** to `get`, `update`, or `delete` (e.g. `client.Project.delete(target)`). The SDK then uses the resource's `tenant_meta.namespace` so the path matches the owning namespace; otherwise using the client default namespace can cause 404 Not Found. See [contracts.md](../contracts.md) (Namespace scoping) and `endorlabs.utils.resolve_namespace_for_resource`.

## Workflow

1. **Document** — Task, context, approach, errors and stack traces.
2. **Research** — Search codebase and docs; review API spec (see [contracts.md](../contracts.md)).
3. **Investigate** — Read SDK code and spec; test with endorctl; validate theories.
4. **Resolve** — Implement fix; document signatures and learnings.

## Slow or hanging list operations

- **Narrow scope** first: list from a **child namespace** without `traverse` before using tenant-wide `traverse=True`.
- **Tighten `filter`** when the resource supports selective filters; avoid broad unfiltered lists on large tenants when possible.
- **Compare with `endorctl`** for the same resource, namespace, filter, and traverse to isolate client vs backend latency.
- **`max_pages`/`page_size`:** Capping pages bounds the client loop; it does not guarantee cheap server-side work for the first page. See [list-query-performance.md](list-query-performance.md).

## List ServerError ("Spec is not full" / "not fully defined")

- The backend may return errors such as `FindingSpec` / `InstallationSpec` / `RepositorySpec` / `PackageVersionSpec` "is not full..." or "not fully defined" when listing at a given namespace (e.g. tenant root). The SDK surfaces these as `ServerError`.
- **Interpretation**: If the API returns 5xx with that message, the SDK is correct to surface it; listing at a child namespace (or different scope) may avoid it. If the API returns 200 but the response body does not match Pydantic models (e.g. partial spec), consider optional/lenient parsing in the SDK only where safe.

### List mask / partial response leniency

- List responses may omit spec-required fields when using a **mask** (`list_params.mask`) or at certain scopes (e.g. tenant root). The OpenAPI spec describes the full resource; list is not guaranteed to return every required field.
- The SDK accepts these partial responses for list via spec-aligned leniency: **Finding** `context` is optional when the list response omits it; **Project** `spec.platform_source` is optional when the list mask omits it; **BaseMeta** `name` is optional when the list mask omits it. Callers that use these fields should handle `None` (e.g. `finding.context`, `project.spec.platform_source`, `resource.meta.name`).

## System-owned resources (authentication_log, endor_license, policy_template)

These resources are system-scoped in the SDK facade. Use `list()` for tenant/system namespace visibility. `get()` is supported only when `namespace="oss"`. `create`, `update`, and `delete` are not exposed on these facades.

## Test skips (short test summary)

When pytest reports skips (403, "No resources in scope", validation errors on update, semgrep "unexpected token null"): run `endorctl api list -r <Resource> --traverse -n <namespace>` (PascalCase for resource, e.g. `Finding`, `Project`) to validate whether the namespace has data; see endorctl docs for options (e.g. `--page-size`, `-o table`). **Warnings:** Run pytest without `--disable-warnings` to see whether the source is pytest, a library, or the SDK.

## Test resource cleanup (CREATE tests)

Every test that **creates** an API resource (and whose resource supports delete) must clean up in the **same test** using try/finally so cleanup runs on pass, assert failure, or exception. `teardown_method` remains as a backup.

**Guaranteed in-test cleanup (try/finally):**

| Resource | Test file | Tests with try/finally |
|----------|-----------|------------------------|
| APIKey | test_api_key.py | test_client_ux_create_api_key |
| ScanProfile | test_scan_profile.py | test_client_ux_create_scan_profile, test_client_ux_update_scan_profile |
| Namespace | test_namespaces.py | test_namespaces_main_flow, test_namespace_update, test_client_ux_create_namespace |
| Policy | test_policy.py | test_exception_policy_create, test_notification_policy_create, test_admission_policy_create, test_client_ux_create_policy |
| SemgrepRule | test_semgrep_rule.py | test_semgrep_rule_create, test_semgrep_rule_update |
| AuthorizationPolicy | test_authorization_policy.py | test_client_ux_create_authorization_policy, test_client_ux_update_authorization_policy |
| ScanProfile (in project test) | test_project.py | test_associate_scan_profile_with_project (delete in existing finally) |

Tests that **create then delete** as the behavior under test (e.g. test_client_ux_delete_api_key) do not add redundant finally-delete.

**Resources with CREATE but no delete API:** scan_log_request is request-based (create returns logs in response); it has no delete, so no try/finally delete is needed. See [resources.md](../reference/resources.md).

**Verifying with endorctl:** To check for leftover test resources in a namespace (e.g. after interrupted runs), use the same namespace as tests (`ENDOR_NAMESPACE` or default `endor-solutions-tgowan`):

- `endorctl api list -r APIKey -n <namespace> --traverse` — API keys (filter by name pattern in output if needed).
- `endorctl api list -r ScanProfile -n <root> --traverse` — scan profiles (tests create at root).
- `endorctl api list -r Namespace -n <namespace> --traverse` — child namespaces.
- `endorctl api list -r Policy -n <root> --traverse -f "meta.tags in ['test','crud-test']"` — test-tagged policies.
- `endorctl api list -r SemgrepRule -n <namespace> --traverse` — semgrep rules.
- `endorctl api list -r AuthorizationPolicy -n <namespace> --traverse` — authorization policies.

**Cleanup guidance:** When cleaning up leftover test resources, delete **only** resources matching strict test name/pattern criteria so legitimate policies and other stable entities are never targeted. For **policies**, both a test tag and a test-only name pattern are required (e.g. name starts with `Test Exception Policy `, `Test Notification Policy `, `Test Admission Policy `, `ClientUX Exception `, or `ClientUX Del `). For **other resources** (ApiKey, ScanProfile, Namespace, SemgrepRule, AuthorizationPolicy), only **name prefix or exact name** is used (no tag). Use the endorctl commands above to list matching resources, then delete individually via `endorctl api delete`.

**Adding new CREATE tests:** Use the same try/finally pattern: create in try, delete in finally (same namespace as create). Keep appending to `created_*_uuids` in the try block so teardown_method can still run as backup.

## References

- OpenAPI/spec path and list/update patterns: [contracts.md](../contracts.md).
- For resolved-case narratives (wrong URL pattern, update_mask, tags): use local docs snapshots under `.endorlabs-context/docs/` or repo issues.
