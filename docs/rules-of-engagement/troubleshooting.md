# Troubleshooting Rules of Engagement

Workflow only. Resolved-case narratives: [docs.endorlabs.com](https://docs.endorlabs.com/) or search repo issues. Workflow below.

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

## References

- OpenAPI/spec path and list/update patterns: [conventions.md](../conventions.md).
- For resolved-case narratives (wrong URL pattern, update_mask, tags): see [docs.endorlabs.com](https://docs.endorlabs.com/) or repo issues.
