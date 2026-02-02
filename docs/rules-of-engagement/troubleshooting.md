# Troubleshooting Rules of Engagement

Workflow below. Resolved-case narratives: [docs.endorlabs.com](https://docs.endorlabs.com/) or search repo issues.

## Platform insight: path namespace vs body UUID

For endpoints that take a **resource UUID in the body** and a **namespace in the path** (e.g. create scan-log-request with `scan_result_uuid`), the path namespace must be the **owning** namespace of that resource (the resource’s `tenant_meta.namespace`). Using a **parent** namespace can return 500 even with a valid UUID. This behavior is not always stated in the API spec; document it in SDK docstrings once confirmed.

**Avoiding 404 after traverse:** When you act on objects returned from `list(traverse=True)` (or broad filters), pass the **resource object** to `get`, `update`, or `delete` (e.g. `client.project.delete(target)`). The SDK then uses the resource's `tenant_meta.namespace` so the path matches the owning namespace; otherwise using the client default namespace can cause 404 Not Found. See [conventions.md](../conventions.md) (Namespace scoping) and `endorlabs.utils.resolve_namespace_for_resource`.

## Workflow

1. **Document** — Task, context, approach, errors and stack traces.
2. **Research** — Search codebase and docs; review API spec (see [conventions.md](../conventions.md)).
3. **Investigate** — Read SDK code and spec; test with endorctl; validate theories.
4. **Resolve** — Implement fix; document signatures and learnings.

## List ServerError ("Spec is not full" / "not fully defined")

- The backend may return errors such as `FindingSpec` / `InstallationSpec` / `RepositorySpec` / `PackageVersionSpec` "is not full..." or "not fully defined" when listing at a given namespace (e.g. tenant root). The SDK surfaces these as `ServerError`.
- **Interpretation**: If the API returns 5xx with that message, the SDK is correct to surface it; listing at a child namespace (or different scope) may avoid it. If the API returns 200 but the response body does not match Pydantic models (e.g. partial spec), consider optional/lenient parsing in the SDK only where safe.

### List mask / partial response leniency

- List responses may omit spec-required fields when using a **mask** (`list_params.mask`) or at certain scopes (e.g. tenant root). The OpenAPI spec describes the full resource; list is not guaranteed to return every required field.
- The SDK accepts these partial responses for list via spec-aligned leniency: **Finding** `context` is optional when the list response omits it; **Project** `spec.platform_source` is optional when the list mask omits it; **BaseMeta** `name` is optional when the list mask omits it. Callers that use these fields should handle `None` (e.g. `finding.context`, `project.spec.platform_source`, `resource.meta.name`).

## Test skips (short test summary)

When pytest reports skips (403, "No resources in scope", validation errors on update, semgrep "unexpected token null"): run `endorctl api list -r <Resource> --traverse -n <namespace>` (PascalCase for resource, e.g. `Finding`, `Project`) to validate whether the namespace has data; see endorctl docs for options (e.g. `--page-size`, `-o table`). **Warnings:** Run pytest without `--disable-warnings` to see whether the source is pytest, a library, or the SDK.

## References

- OpenAPI/spec path and list/update patterns: [conventions.md](../conventions.md).
- For resolved-case narratives (wrong URL pattern, update_mask, tags): see [docs.endorlabs.com](https://docs.endorlabs.com/) or repo issues.
