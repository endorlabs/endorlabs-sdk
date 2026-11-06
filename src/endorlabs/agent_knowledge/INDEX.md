# Endor Labs SDK — Agent Index (Tier 0)

Shipped with `endorlabs` inside the wheel. **`endorlabs.init()` is optional** — use
`agent_knowledge_index_path()` to read this file from site-packages, or materialize under
`.endorlabs/_cache/sdk/` when a cwd-relative tree is needed.

## First steps (agents and humans)

```python
import endorlabs

# 0. Map — no credentials (print is human-readable; do not rely on dataclass repr)
print(endorlabs.discover())
# Or: python -m endorlabs.examples.agent_bootstrap --dry-run

d = endorlabs.discover()
# Read every path in d.bootstrap_paths.

# 0b. Resource kwargs / routes — no credentials (deferred auth on Client)
client = endorlabs.Client(tenant="your-tenant")
print(client.Finding.describe())  # stub is for IDE typing only

# 1. Auth — live API (whoami / list / get)
print(client.whoami())  # None → check .env / single auth mode

# 2. Workflows — call graph, scan RCA, project bundles (not on dir(client))
status = endorlabs.init(include_openapi=False)
# Read .endorlabs/_cache/sdk/skills/<id>/SKILL.md
```

## Agents — step zero (required)

Before `endorlabs.Client()` or live API calls:

1. `print(endorlabs.discover())` or `python -m endorlabs.examples.agent_bootstrap --dry-run` — then **read every path** in `bootstrap_paths`.
2. Prefer `print(client.<Kind>.describe())` for resource-specific `list()` identity kwargs and route accessors (no network). `Client()` without credentials is enough — auth runs on first API call, not on describe. Read `discover().stub` only when you need IDE/static typing — not as the primary kwargs source.
3. **Auth check:** `Client().whoami()` — do not use `Namespace.list()` as an auth proxy.
4. **Workflows** (call graph, project bundle, scan RCA): `endorlabs.init()` → read `skills/<id>/SKILL.md` (start: **endor-fetch-and-search-call-graph**, **endor-retrieve-scan-results**)

Skipping step 1–2 causes repeatable traps (`filter=`, namespace scoping, mask→dict, auth mode).
Consumer entrypoint: **`AGENTS.md`** (points here). Copy **`templates/consumer-AGENTS.md`** to your project root.

## Day-0 traps

| Trap | Correct pattern |
|------|-----------------|
| Stub as kwargs source | Prefer `print(client.Finding.describe())` — live identity kwargs + routes; stub is for typing |
| `F()` positional | `list(filter=F("spec.level") == "…", traverse=True)` — never `list(F(...) == …, traverse=True)` |
| `F.field` attribute | Use `F("spec.field")` — dotted paths are strings, not attributes on `F` |
| `from endorlabs.filters import F` | `from endorlabs import F` — `endorlabs.filters` is MQL fragments only |
| `ScanResult.list(filter=…spec.project_uuid…)` | `ScanResult.list_by_project(project)` — project link is `meta.parent_uuid` (same for FindingLog); Finding/PV use `spec.project_uuid` |
| `list_by_*` / `list_for_context` expecting wrong return type | `list[T]` — same as `.list()`; project/scan-plane edges |
| `to_*` expecting wrong return type | `RouteResult` — stitch; `.value` / `.single`; check `.edge_used`, `.warnings` |
| `limit` on `.list()` | Use `page_size=` or `limit=` (alias for `page_size`; same as `list_by_project(limit=)`) |
| Sorted list + `max_pages>1` | Platform rejects `page_id` with sort — use `limit=`/`page_size` + `max_pages=1`, or drop `sort_by` ([list-parameters](contracts/list-parameters.md)) |
| Finding text field | `spec.summary`, not `spec.description` |
| `Metric.list_by_project` | Does not exist — use `Metric.list(...)` with filters |
| `QueryVulnerability.list` | Query resources are create/query only, not listable CRUD |
| `endorlabs.query_vulnerability` | Submodule for payload builders — use `client.QueryVulnerability` |
| MCP + SDK + endorctl auth | **One mode** in `.env`: `ENDOR_TOKEN` **or** key+secret, not both |
| Call graph: `fetch()` only | Use `CallGraphData.decode()` for searchable callables/edges; `fetch()` is raw envelope |
| `call_graph_available=true` | Flag ≠ stored data — use `resolve_package_version_with_callgraph()` |
| Call graph helpers | Not on `client` — `endorlabs.workflows.callgraph` + skill **endor-fetch-and-search-call-graph** |
| `repr(discover())` / dataclass repr | Use `print(discover())` or `agent_bootstrap --dry-run` — `SdkDiscovery` has a readable `__str__` |
| Auth via `Namespace.list()` | Use `Client().whoami()` after credentials are set |
| Filter enum literals | Examples in [reference/filter-enum-snippets.md](reference/filter-enum-snippets.md) |

Return types (normative): [contracts/resource-discovery.md](contracts/resource-discovery.md).

**Beyond Day-0:** [reference/critical-validation-traps.md](reference/critical-validation-traps.md) (namespace RCA, masks, malware planes). Glossary: [reference/product-ontology.md](reference/product-ontology.md). App URL templates: [reference/endor-app-url-templates.md](reference/endor-app-url-templates.md). Catalog: `MANIFEST.json` → `references[]`.

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

status = endorlabs.init(include_openapi=False)
# Read: status.agent_knowledge_index_path  →  .endorlabs/_cache/sdk/INDEX.md
```

**Full bootstrap** (agent knowledge + platform OpenAPI):

```python
import endorlabs

status = endorlabs.init(include_openapi=True)
# Read: status.agent_knowledge_index_path
# Product docs: configure Docs MCP — https://docs.endorlabs.com/introduction/docs-mcp-server
# Unsupported harnesses: https://docs.endorlabs.com/llms.txt
```

## Authentication

Set credentials via environment (never commit secrets):

- `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`, or
- `ENDOR_TOKEN` (browser SSO — refresh with `uv run endor-auth refresh --method sso -n <tenant>`)
- Optional default namespace: `ENDOR_NAMESPACE` (or `~/.endorctl/config.yaml` after `endorctl init`)

Probe and verify: `uv run endor-auth check [--tenant <tenant>]`. Skill: **endor-auth-setup**.
Verify in code: `endorlabs.Client().whoami()`.

## Client basics

```python
import endorlabs
client = endorlabs.Client(tenant="tenant.namespace")
projects = client.Project.list(traverse=True, max_pages=2)
```

- Resource facades use **PascalCase**: `client.Project`, `client.Finding`, …
- Match `endorctl api … --resource <Kind>` vocabulary.
- Return types: [contracts/resource-discovery.md](contracts/resource-discovery.md) (Day-0 trap rows above).
- Prefer `print(client.<Kind>.describe())` for identity kwargs, top `spec.*` filter paths, and the filter-enum snippets link.

## Bootstrap (load for Endor SDK work)

Harnesses should prepend `agent_knowledge_bootstrap_paths()` (or read these rules first). In Cursor, `endor-namespace-scoping` and `endor-list-query-performance` are **always-on**; other bootstrap `endor-*.mdc` rules attach when path **globs** match (`src/endorlabs/**`, Python, `.endorlabs/`, etc.).

| Rule | Summary |
|------|---------|
| `endor-namespace-scoping` | Resolve Project; pass `namespace=project.namespace` on project-scoped lists |
| `endor-workspace-layout` | Artifacts under `tasks/<slug>-<YYYY-MM-DD>/`, `reports/`, or flat `tasks/<activity>/` |
| `endor-workflow-composition` | CLI → library → Client → session script; artifact-first |
| `endor-list-query-performance` | Do not set `page_size` unless asked |
| `endor-local-context` | Check gitignored `.endorlabs/` paths explicitly |
| `endor-portable-examples` | Placeholders only across tracked surfaces (fixtures, docs, skills); no tenant/email/UUID literals |

See `MANIFEST.json` → `bootstrap.rule_ids` and `bootstrap.contract_ids` for the machine-readable lists.

## Evidence vs inference

Label conclusions clearly when reporting to users:

- **Evidence-backed:** API rows (`list`/`get`), workflow artifacts (`context_manifest.json`, troubleshooting JSON), `endorctl` output, or normative text in `contracts/` and skill steps you executed. Quote resource UUIDs, namespaces, and error text from those sources.
- **Inferred:** Heuristic rankings, partial bundle coverage, model guesses about backend intent, or “likely cause” without a reproducing call. Prefix with **Inferred:** and state what evidence is missing.

App URL templates for citations: [reference/endor-app-url-templates.md](reference/endor-app-url-templates.md).

## Skills vs workflow CLIs

- **Skills** (`skills/<id>/SKILL.md`) are agent **playbooks** — read the file, follow steps.
- **Workflow CLIs** (`endor-*`, `python -m endorlabs.workflows…`) are what you **run**; discover names via `print(endorlabs.discover())` → `entry_points` or `MANIFEST.json` → `workflows[]`.
- Materialize playbooks: `endorlabs.init()` → `.endorlabs/_cache/sdk/skills/`; optional `init(sync_skills="both")` (`.agents/skills/` + `.claude/skills/`).

## Progressive disclosure

1. **Metadata** — skill `description` in `MANIFEST.json` (WHAT + WHEN).
2. **Playbook** — `skills/<id>/SKILL.md` when triggered.
3. **References** — `MANIFEST.json` → `references[]`, `contracts/`, sibling skills.

## Workspace outputs

See `rules/endor-workspace-layout.md`. Prefer `tasks/<slug>-<YYYY-MM-DD>/…` and `reports/`; gitignore `.endorlabs/` in consumer projects.

## Read order

1. This file (Tier 0)
2. `MANIFEST.json` — rules, contracts, skills, workflows, `references[]`, `bootstrap`
3. **`rules/*.md`** — harness bootstrap (always load)
4. **`reference/*.md`** — critical traps, ontology, URL templates, filter enums (on demand)
5. **`contracts/*.md`** — normative SDK semantics on demand
6. **`skills/*/SKILL.md`** — task playbooks
7. `.endorlabs/_cache/openapi.json` — OpenAPI after `init(include_openapi=True)`; product docs via Docs MCP (`https://docs.endorlabs.com/mcp`)
8. `.endorlabs/reports/` and `.endorlabs/tasks/` — your run outputs

## Task routing (common intents)

| Intent | Start skill |
|--------|-------------|
| Credential setup / refresh | `endor-auth-setup` |
| Findings / scan results for one repo | `endor-retrieve-scan-results` |
| Scan pipeline RCA | `endor-troubleshooting-scans` |
| Call graph search | `endor-fetch-and-search-call-graph` |
| AI-SAST → Call Graph bridge | `endor-aisast-callgraph-bridge` |
| Project context bundle | `endor-project-retrieval-bundle` |
| Policy validation | `endor-validate-policy` |
| SDK/API errors | `endor-troubleshoot-sdk` |
| Login / SSO troubleshooting | `endor-troubleshoot-authlog` |
| Login activity CSV | `endor-workflow-reports` → `endor-reports login-count -n <tenant>` |
| Duplicate projects audit | `endor-workflow-reports` → `endor-reports duplicates -n <tenant>` |
| CLI vs Cloud classification | `endor-workflow-reports` → `endor-reports cli-vs-cloud -n <tenant>` |
| Onboarding config presence | `endor-config-presence` → `endor-config-presence -n <tenant> [--project <uuid>]` |

Full catalog: `MANIFEST.json` → `skills[]`.

## Maintainer docs (not shipped)

Repo-only: `CONTRIBUTORS.md`, `docs/contributing/`, `devtools/`. Clone the GitHub repo for those.
