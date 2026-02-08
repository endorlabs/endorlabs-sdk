# Namespace (AF)

Namespace in the AF: list, get, create, update, delete. Parameters use canonical name and UUID. Full platform concepts (hierarchy, tenant isolation): [docs.endorlabs.com](https://docs.endorlabs.com/).

## Operations

- **List**: `namespace.list_namespaces(client, tenant_namespace, list_params=None, max_pages=None)` — list child namespaces under a tenant (canonical name).
- **Get**: `namespace.get_namespace(client, tenant_meta_namespace, namespace_uuid)` — fetch one namespace by parent and UUID.
- **Create**: `namespace.create_namespace(client, tenant_meta_namespace, payload)` — payload: `CreateNamespacePayload` with `meta` (name, description).
- **Update**: `namespace.update_namespace(client, tenant_meta_namespace, namespace_uuid, payload, update_mask)` — **update_mask required** (e.g. `"meta.description"`). Same collection PATCH pattern as other resources; API returns 400 if no field mask.
- **Delete**: `namespace.delete_namespace(client, tenant_meta_namespace, namespace_uuid)` — cascades to children.

## Parameters

- Use **canonical namespace** (e.g. `tenant.namespace.child`), not UUIDs, for `tenant_meta_namespace` / `tenant_namespace`.
- Update mutable fields: `meta.description`, `meta.name`, `meta.tags`, `spec.managed` (per API spec). Immutable: uuid, meta.create_time, meta.update_time, etc.

## Common pitfalls

- Using UUID instead of canonical name for parent namespace — use `tenant.namespace` form.
- Omitting `update_mask` on update — namespace requires at least one field (e.g. `"meta.description"`).
- Cross-tenant operations — ensure all operations use the same tenant namespace.

Runnable patterns: `tests/`, `maneuvers/`.
