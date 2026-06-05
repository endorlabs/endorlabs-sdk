---
id: portable-examples
tags: [examples, hygiene, placeholders]
tier: bootstrap
summary: >-
  Use placeholders in git-tracked agent content; never commit customer estate
  identifiers (tenants, project URLs, production UUIDs).
---

# Portable examples

Git-tracked agent skills, contracts, and generated bundle content must not embed
**estate identifiers** from customer organizations.

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

## Qualified exception

**`endorlabs/endorlabs-sdk`** (this repository's public URL) may appear when labeled
as the **canonical SDK integration-test fixture**, not as a customer estate example.

## Runtime resolution

- Tenant/namespace: `ENDOR_NAMESPACE`, CLI `--tenant` / `--namespace`, or `Client(tenant=…)`.
- Project: user-provided URL/UUID or `Project.list` / `resolve_project` at runtime.
- Never hardcode 24-hex UUIDs in skills or contracts.
