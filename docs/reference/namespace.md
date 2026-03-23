# Namespace (SDK)

Namespace in the SDK: list, get, create, update, delete. Parameters use canonical name and UUID.

## Operations

- **List**: `client.Namespace.list(traverse=True, namespace="tenant")` — list child namespaces under a tenant (canonical name).
- **Get**: `client.Namespace.get(uuid, namespace="tenant")` — fetch one namespace by UUID.
- **Create**: `client.Namespace.create(payload=CreateNamespacePayload(...), namespace="tenant")` — payload with `meta` (name, description).
- **Update**: `client.Namespace.update(uuid, payload=..., update_mask="meta.description", namespace="tenant")` — **update_mask required** for UUID+payload updates.
- **Delete**: `client.Namespace.delete(uuid, namespace="tenant")` — cascades to children.

## Parameters

- Use **canonical namespace** (e.g. `tenant.namespace.child`), not UUIDs, for `tenant_meta_namespace` / `tenant_namespace`.
- Update mutable fields: `meta.description`. Immutable includes `uuid`, `meta.name`, `meta.create_time`, `meta.update_time`, and `tenant_meta.namespace`.

## Common pitfalls

- Using UUID instead of canonical name for parent namespace — use `tenant.namespace` form.
- Omitting `update_mask` on UUID+payload update.
- Cross-tenant operations — ensure all operations use the same tenant namespace.

Runnable patterns: `tests/`.
