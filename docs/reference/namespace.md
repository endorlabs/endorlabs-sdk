# Namespace (SDK)

Namespace in the SDK: list, get, create, update, delete. Parameters use canonical name and UUID. Full platform concepts (hierarchy, tenant isolation): [docs.endorlabs.com](https://docs.endorlabs.com/).

## Operations

- **List**: `client.namespace.list(traverse=True, namespace="tenant")` — list child namespaces under a tenant (canonical name).
- **Get**: `client.namespace.get(uuid, namespace="tenant")` — fetch one namespace by UUID.
- **Create**: `client.namespace.create(payload=CreateNamespacePayload(...), namespace="tenant")` — payload with `meta` (name, description).
- **Update**: `client.namespace.update(uuid, payload=..., update_mask="meta.description", namespace="tenant")` — **update_mask required**. Same collection PATCH pattern as other resources; API returns 400 if no field mask.
- **Delete**: `client.namespace.delete(uuid, namespace="tenant")` — cascades to children.

## Parameters

- Use **canonical namespace** (e.g. `tenant.namespace.child`), not UUIDs, for `tenant_meta_namespace` / `tenant_namespace`.
- Update mutable fields: `meta.description`, `meta.name`, `meta.tags`, `spec.managed` (per API spec). Immutable: uuid, meta.create_time, meta.update_time, etc.

## Common pitfalls

- Using UUID instead of canonical name for parent namespace — use `tenant.namespace` form.
- Omitting `update_mask` on update — namespace requires at least one field (e.g. `"meta.description"`).
- Cross-tenant operations — ensure all operations use the same tenant namespace.

Runnable patterns: `tests/`.
