# SDK Conventions

Single source of truth for Endor Cockpit SDK usage. Link here from other docs instead of re-stating.

## Canonical naming

- Use `tenant.namespace.child` only; never UUIDs in namespace paths.
- Example: `tenant_meta_namespace="endor-solutions-tgowan"` or `"tenant.bu.team"`.

## OpenAPI / spec

- The spec is not in the repo; use <https://api.endorlabs.com/download/openapiv2.swagger.json>. The schema drift workflow downloads it to `external_docs/openapi-swagger.json` (gitignored) in CI.
- List endpoints: `v1/namespaces/{tenant_meta.namespace}/{resource_name}` (e.g. `findings`, `projects`).
- Update (PATCH): Collection URL; UUID and payload in request body; optional `request.update_mask`.

## Traverse

- `ListParameters(traverse=True)` for tenant-wide list operations.
- Pass to the resource's `list_*` function; the client sends `list_parameters.traverse=true`.
- Use when namespace is unknown or you need all child namespaces.

## List parameters

- **filter**: `list_params.filter` → `list_parameters.filter` (e.g. `spec.level==FINDING_LEVEL_CRITICAL`).
- **mask**: `list_params.mask` → `list_parameters.mask` (e.g. `meta.name,spec.level`) for response field selection.
- **page_size**, **page_token**: Pagination; only set `page_size` when you need a specific size (API default otherwise).
- **sort_field**, **sort_order**: Sorting.
- **traverse**: See above.
- Defined in `endor_cockpit.types.ListParameters`; see [src/endor_cockpit/types.py](../src/endor_cockpit/types.py).

## Update and update_mask

- Most resources: `update_*` accepts optional `update_mask: str` (comma-separated paths). When present, the base layer builds a sparse request body and sends `request.update_mask`.
- Namespace: `update_mask` is **required** (e.g. `"meta.description"`); API returns 400 without at least one field.
- Immutable fields in `update_mask` are rejected by the SDK before the request.

## Errors

- Use `endor_cockpit.exceptions`; resources may return `None` on 404 where documented.
- Log full `response.text` on errors; no truncation in error handling.
- gRPC-derived status codes are mapped to HTTP and typed exceptions where documented.
