---
id: endor-portable-examples
tags: [examples, hygiene, placeholders]
summary: >-
  Use placeholders in git-tracked agent content; never commit customer estate
  identifiers (tenants, project URLs, production UUIDs).
---

# Portable examples

Git-tracked agent skills, contracts, and generated bundle content must not embed
**estate identifiers** from customer organizations. There is **no** automated
substring allowlist—apply judgment using the classes below.

## Name classes

| Class | Meaning | In git-tracked agent content |
|-------|---------|------------------------------|
| **Placeholders** | `<tenant>`, `<namespace>`, `<project-uuid>`, `tenant.namespace`, `https://github.com/org/repo.git` | **Required** in commands and snippets |
| **Product vocabulary** | Platform features, connector types, resource kinds, scan categories in product/user-docs | OK when describing *how the product works* |
| **Estate identifiers** | Tenant roots, child namespaces, registered project URLs/names, production UUIDs | **Never** commit; resolve from env, user input, or API at runtime |

## Integration surface vs inventory record

A label may name a **platform integration surface** (documented connector or SCM
capability) or a **tenant-owned inventory record** (a Project UUID or registered
repository URL). Portable docs use only the former class generically; inventory
records are session data.

When unsure, prefer a placeholder. Do not add repo-specific "exceptions" for
particular customer names, tenant paths, or UUIDs—those belong in session context,
integration tests with env vars, or user-provided inputs.

## Runtime resolution

- Tenant/namespace: `ENDOR_NAMESPACE`, CLI `--tenant` / `--namespace`, or `Client(tenant=…)`.
- Project: user-provided URL/UUID or `Project.search_by_name` / `Project.get` at runtime.
- Never hardcode production UUIDs in skills or contracts.
