---
id: endor-portable-examples
tags:
- examples
- hygiene
- placeholders
- tests
- fixtures
summary: Use placeholders in all git-tracked content; never commit customer estate
  identifiers, PII, or secrets (tenants, project URLs, production UUIDs, emails) across
  docs, skills, unit fixtures, docstrings, and CLI examples.
---

# Portable examples

**All git-tracked content** must not embed **estate identifiers** or **PII** from
customer organizations. That includes agent skills and docs **and** unit-test
fixtures, module docstrings, argparse help, probe/CLI examples, changelogs, and
comments. There is **no** automated substring allowlist for every case—apply
judgment using the classes below; pre-commit covers the high-confidence patterns.

## Surfaces in scope

| Surface | Rule |
|---------|------|
| **Unit tests / fixtures** | Use `example-tenant`, `user@example.com` / `user@endor.ai`, `example-tenant.child`, fake opaque ids. Never paste real login-count rows, auth identities, or customer tenants into `tests/`. |
| **Integration tests** | Real tenant via **env** only (`ENDOR_NAMESPACE`, secrets)—not committed literals. Default local namespace may be a non-customer lab value (e.g. `auri`); never a customer root. |
| **Docstrings / CLI help / comments** | Same placeholders as docs. No `-n <customer>` or `tenant="<customer>"` in examples. |
| **Agent skills, contracts, rules** | Placeholders in commands and snippets (`<tenant>`, `<namespace>`, `<project-uuid>`). |
| **Docs / CONTRIBUTORS / README / changelog** | No customer tenants, emails, or production UUIDs. |
| **devtools / probes / scripts** (if tracked) | Example flags only (`-n example-tenant`). Prefer gitignored workspace for live customer runs. |
| **Generated / mirrored** (`src/endorlabs/generated/`, shipped `agent_knowledge/`) | Do not hand-edit to add estate data; authoring under `agent-knowledge/` must stay portable before sync. |

**Out of git (OK for real estate):** `.endorlabs-context/workspace/`, `.tmp/`, local `.env` — never stage those (pre-commit blocks `.env` / `.endorlabs-context/`).

## Name classes

| Class | Meaning | In git-tracked content |
|-------|---------|------------------------|
| **Placeholders** | `<tenant>`, `<namespace>`, `<project-uuid>`, `tenant.namespace`, `example-tenant`, `https://github.com/org/repo.git`, `user@example.com`, `user@endor.ai` | **Required** in commands, snippets, and fixtures |
| **Product vocabulary** | Platform features, connector types, resource kinds, scan categories | OK when describing *how the product works* |
| **Estate identifiers** | Customer tenant roots, child namespaces, registered project URLs/names, production UUIDs | **Never** commit; resolve from env, user input, or API at runtime |
| **PII** | Customer or end-user emails, names, auth identities, account ids | **Never** commit; use placeholders above |

## Secrets

Never commit API keys, bearer tokens, `.env` files, or credential files. Pre-commit runs **gitleaks** on staged changes. Confirm env vars exist without printing values (rule `endor-local-context`).

Pre-commit also **fails** (checked-in staged paths) on:

- Non-placeholder emails and non-Endor URLs on *added* lines (`external-pii-urls`)
- Estate `-n` / `--namespace` / `--tenant` tokens on *added* lines (placeholders only:
  `example-tenant`, `<tenant>`, `{tenant}`, `$ENDOR_NAMESPACE`, `auri`, `oss`, …)
- **Shipped** `src/endorlabs/**` (full tree, every commit): same `-n` / `--namespace` /
  `--tenant` placeholder rule — non-placeholder values cannot ship in the wheel
- High-confidence estate literals (`portable-examples`: customer GitHub URLs, dotted tenant paths)

Allowed email domains: `@example.*`, `@endorlabs.com`, `@endor.ai`.

## Integration surface vs inventory record

A label may name a **platform integration surface** (documented connector or SCM
capability) or a **tenant-owned inventory record** (a Project UUID or registered
repository URL). Portable docs and tests use only the former class generically;
inventory records are session data or env-driven integration inputs.

When unsure, prefer a placeholder. Do not add repo-specific "exceptions" for
particular customer names, tenant paths, or UUIDs.

## Runtime resolution

- Tenant/namespace: `ENDOR_NAMESPACE`, CLI `--tenant` / `--namespace`, or `Client(tenant=…)`.
- Project: user-provided URL/UUID or `Project.search_by_name` / `Project.get` at runtime.
- Never hardcode production UUIDs or customer emails in skills, contracts, or unit fixtures.
