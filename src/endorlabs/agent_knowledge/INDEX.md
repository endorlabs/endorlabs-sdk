# Endor Labs SDK — Agent Index (Tier 0)

Shipped with `endorlabs` inside the wheel. **`endorlabs.init()` is optional** — use
`agent_knowledge_index_path()` to read this file from site-packages, or materialize under
`.endorlabs-context/sdk/` when a cwd-relative tree is needed.

## Quick start

**Wheel-only** (no disk materialization):

```python
import endorlabs

print(endorlabs.agent_knowledge_index_path())
manifest = endorlabs.agent_knowledge_manifest()
paths = endorlabs.agent_knowledge_bootstrap_paths()  # INDEX + bootstrap rules
```

**Minimal bootstrap** (rules, contracts, skills; no auth):

```python
import endorlabs

status = endorlabs.init(include_openapi=False, include_user_docs=False)
# Read: status.agent_knowledge_index_path  →  .endorlabs-context/sdk/INDEX.md
```

**Full bootstrap** (agent knowledge + platform OpenAPI/user docs):

```python
pip install 'endorlabs[docs]'
import endorlabs

status = endorlabs.init(include_openapi=True, include_user_docs=True)
# Read: status.agent_knowledge_index_path
```

## Authentication

Set credentials via environment (never commit secrets):

- `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`, or
- `ENDOR_TOKEN` (browser refresh via maintainer tooling writes this only)
- Optional default namespace: `ENDOR_NAMESPACE`

Verify: `endorlabs.Client().whoami()`.

## Client basics

```python
import endorlabs
client = endorlabs.Client(tenant="tenant.namespace")
projects = client.Project.list(traverse=True, max_pages=2)
```

- Resource facades use **PascalCase**: `client.Project`, `client.Finding`, …
- Match `endorctl api … --resource <Kind>` vocabulary.
- `.get()` returns typed models; `.list()` / `search_by_*` return models unless `mask=` is set; `list_by_*` returns `RouteResult`.

## Critical validation traps

Read **`rules/`** (Tier 1 bootstrap) before project-scoped RCA. When behavior
looks wrong, **triangulate** SDK vs `endorctl` vs `contracts/` — skill
**endor-troubleshoot-sdk** ([`validation-reference.md`](skills/endor-troubleshoot-sdk/validation-reference.md)).

1. **Ambiguous project URL:** `Project.search_by_name(..., traverse=True, max_pages=…)` returns bounded candidates — pick the row for the intended namespace, narrow `namespace=`, or use project UUID with `get()`.
2. **Project-scoped list namespace (MUST):** With `Client(tenant=<estate_root>)` and default
   `traverse=False`, lists hit only that path segment—not child namespaces where projects live.
   Resolve `Project` first, then pass **`namespace=project.namespace`** on `Finding`, `ScanResult`,
   `PackageVersion`, `DependencyMetadata`, … Empty rows often mean wrong namespace, not missing data.
3. **Finding branch refs:** `spec.source_code_version.ref` may be a short branch label, not
   `refs/heads/main`. List findings without branch filter first; narrow after inspecting stored refs.
4. **Tenant-wide scan cost:** `fetch_scan_results --all-projects` is O(projects × scans). Prefer
   project-scoped RCA.
5. **List masks:** Non-empty `mask=` on `.list()` / `search_by_*` returns `dict` rows, not Pydantic models.
6. **DependencyMetadata wire path:** List/group uses the **customer tenant namespace**, not the
   literal `oss` plane. Field `spec.dependency_data.namespace == "oss"` is data semantics only.
7. **Workflow composition:** Extend workflow JSON/manifests before re-listing the API; escalate
   CLI → library → `Client` → session script (see `rules/endor-workflow-composition.md`).
8. **Portable examples:** Use placeholders in docs; never commit customer estate identifiers
   (`rules/endor-portable-examples.md`).

## Bootstrap (load for Endor SDK work)

Harnesses should prepend `agent_knowledge_bootstrap_paths()` (or read these rules first). In Cursor, `endor-namespace-scoping` and `endor-list-query-performance` are **always-on**; other bootstrap `endor-*.mdc` rules attach when path **globs** match (`src/endorlabs/**`, Python, `.endorlabs-context/`, etc.).

| Rule | Summary |
|------|---------|
| `endor-namespace-scoping` | Resolve Project; pass `namespace=project.namespace` on project-scoped lists |
| `endor-workspace-layout` | Session artifacts under `workspace/sessions/<user>/` |
| `endor-workflow-composition` | CLI → library → Client → session script; artifact-first |
| `endor-list-query-performance` | Do not set `page_size` unless asked |
| `endor-local-context` | Check gitignored `.endorlabs-context/` paths explicitly |
| `endor-portable-examples` | Placeholders only; no committed tenant/project UUID literals |

See `MANIFEST.json` → `bootstrap.rule_ids` for the machine-readable list.

## Evidence vs inference

Label conclusions clearly when reporting to users:

- **Evidence-backed:** API rows (`list`/`get`), workflow artifacts (`context_manifest.json`, troubleshooting JSON), `endorctl` output, or normative text in `contracts/` and skill steps you executed. Quote resource UUIDs, namespaces, and error text from those sources.
- **Inferred:** Heuristic rankings, partial bundle coverage, model guesses about backend intent, or “likely cause” without a reproducing call. Prefix with **Inferred:** and state what evidence is missing.

For SDK/API validation playbooks, load **`skills/endor-troubleshoot-sdk/SKILL.md`** and [`validation-reference.md`](skills/endor-troubleshoot-sdk/validation-reference.md). Repo clone only: `docs/contributing/troubleshooting.md` (not shipped in the wheel).

## Workspace outputs

Session/triage debugging artifacts and temporary probe scripts belong under
`.endorlabs-context/workspace/sessions/<user>/` (not repo-root `.tmp/`). Project
bundles go under `workspace/projects/<uuid>/`. See `rules/endor-workspace-layout.md`.

## Read order

1. This file (Tier 0)
2. `MANIFEST.json` — rules, contracts, skills, workflow CLI index, `bootstrap` block
3. **`rules/*.md`** — harness bootstrap (always load)
4. **`contracts/*.md`** — normative SDK semantics on demand
5. **`skills/*/SKILL.md`** — task playbooks
6. `../platform/openapi/` and `../platform/user-docs/` — product/API reference (after `init()`)
7. `../workspace/` — your run outputs

## Maintainer docs (not shipped)

Repo-only: `CONTRIBUTORS.md`, `docs/contributing/`, `devtools/`. Clone the GitHub repo for those.
