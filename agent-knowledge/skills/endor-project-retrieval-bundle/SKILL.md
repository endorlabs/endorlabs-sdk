---
name: endor-project-retrieval-bundle
description: |
  Use when building a deterministic single-project retrieval bundle via
  endor-agent-context: context_manifest.json, dependency explorer artifacts,
  optional session summaries, PV index + hydration, optional call-graph export. Not
  for namespace topology or breaking-change consumer discovery—hand off to
  endor-namespace-relationship-map.
endorlabs:
  catalog:
    workflow_id: agent-context
    cli: endor-agent-context
    module: endorlabs.workflows.agent_context.cli
    default_output: .endorlabs-context/workspace/projects/<slug>_<timestamp>/
    agent_visible: true
    composition: library_api
    library_entrypoints:
      - endorlabs.workflows.agent_context.build_context_manifest
      - endorlabs.workflows.agent_context.list_package_versions_for_index
      - endorlabs.workflows.callgraph.run_callgraph_export
---

# Project retrieval bundle

Read `context_manifest.json` first; composition rules in [workflow-composition](../../rules/endor-workflow-composition.md).

## Purpose

Produce a **versioned, machine-readable retrieval bundle for one project** via **`endor-agent-context`** (not `endor-estate`). This is the shared **retrieval layer** for SBOM slices, DependencyMetadata, optional findings/policies/versions summaries, and call-graph exports — not namespace topology or “who must I warn about a breaking change?”

## Vocabulary

| Term | Meaning |
|------|---------|
| **Client tenant** | `--tenant` on export — auth context for `endorlabs.Client`. |
| **`--namespace` (optional)** | Disambiguates project lookup only; export remains **one project**. |
| **`--project`** | Required — single repo (UUID or name). |
| **Not namespace scope** | Multi-repo / blast-radius → [endor-namespace-relationship-map](../endor-namespace-relationship-map/SKILL.md); bulk namespace pull → [docs/estate/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/estate/README.md) (user must request). |

## Decision table

| Question | Use this skill | Hand off to |
|----------|----------------|-------------|
| SBOM / DM / PV index-hydration for **one repo** | `uv run endor-agent-context` | — |
| Findings/policies/repo-version **summaries in the bundle** | add `--session-summaries` | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) for scan RCA |
| **Who consumes packages my repo produces** (breaking-change blast radius) | — | [endor-namespace-relationship-map](../endor-namespace-relationship-map/SKILL.md) with `--focus-producer-project-uuid`, or `endor-estate analyze -n <namespace_scope> --only-relationships --focus-producer-project-uuid` |
| Full namespace project graph (all edges) | — | namespace relationship map or `endor-estate analyze --only-relationships` |
| Bulk pull/analyze under a **namespace scope** (explicit user request) | — | [docs/estate/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/estate/README.md) (`endor-estate`) |
| Function-level call graph search | `--callgraph-export` + `--decode-zstd` | [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) — **read manifest first**; do not decode arbitrary PVs before export |
| Stitched vulnerable-function reachability | bundle as input | `endor-reachability-context` → [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |

**Not `endor-estate`:** this skill is always **single-project** (`--project`). `endor-estate` uses **namespace scope** for multi-project workspace work.

## Ordering

1. **Credentials** — `uv run --env-file .env`. Never paste secrets into skills or logs.
2. **Export** — `uv run endor-agent-context` with `--tenant`, `--project`, optional `--namespace`, `--output-dir`. **Done** when `context_manifest.json` exists. Ambiguous repo URL → **`--namespace`** or **24-hex project UUID** ([AGENTS.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/AGENTS.md#agent-notes)).
3. **Optional session layer** — `--session-summaries` → `artifacts.session_summaries` in the manifest (counts + paths; read summaries only when needed).
4. **Read manifest** — [multipass-llm-contract.md](multipass-llm-contract.md) for bounds (`inventory.truncated`, `--pv-limit`, session block).
5. **Downstream** — relationship map for cross-repo impact, scan skills for posture, call-graph search as needed.

## Multi-pass behavior

| Pass | Role | Default |
|------|------|---------|
| **1 — Index** | `package_versions_index.json` | **On**; `--no-pv-index` to skip |
| **2 — Hydrate** | BOM + CG + DependencyMetadata | **On** unless `--index-only` |
| **3 — Export** | Full PV call-graph export | `--callgraph-export` (+ `--decode-zstd` for search) |

Pass 3 writes `artifacts.callgraph_export` in `context_manifest.json`. **Call-graph export does not populate vector stores** — semantic function summaries use tenant `VectorStore` / `VectorStoreQuery` / `endor-vector-query` separately.

**Hand off:** After Pass 3, follow [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) for path search (direct edges **and** multi-hop BFS when wrappers sit between source and target).

**Bounds:** Pass 2 default **`--pv-limit` 5** — do not infer repo-wide dependency/call-graph posture from the summary alone; escalate via manifest `warnings` or `--hydrate-top-n` / `--hydrate-pv-uuids` ([multipass-llm-contract.md](multipass-llm-contract.md)).

## CLI entrypoints

| Step | Path |
|------|------|
| Export + manifest | `endor-agent-context` / `endorlabs.workflows.agent_context.export` |
| Session summaries | `--session-summaries` |
| PV index helpers | `endorlabs.workflows.agent_context.package_versions` |
| Call-graph export | `--callgraph-export` |

## Key flags

- **Core:** `--tenant`, `--project`, `--namespace`, `--output-dir`
- **Pass 1:** `--no-pv-index`, `--pv-index-max-pages`, `--pv-index-page-size`
- **Pass 2:** `--index-only`, `--pv-limit`, `--dep-metadata-max-pages`, `--hydrate-pv-uuids`, `--hydrate-top-n`
- **Pass 3:** `--callgraph-export`, `--callgraph-max-pages`, `--decode-zstd`
- **Session:** `--session-summaries`
- **`--deterministic`** — stable ordering for replay/diff

## Outputs

- **Bundle:** `<output_dir>/<slug>_<timestamp>/` with `context_manifest.json` (version **2**), optional index, dependency explorer files, optional `callgraph_export/`, optional session subdir.
- **Stdout:** absolute path to `context_manifest.json`.

## Linked skills

- [endor-namespace-relationship-map](../endor-namespace-relationship-map/SKILL.md) — namespace consumer→producer edges
- [docs/estate/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/estate/README.md) — bulk namespace-scoped pull/analyze (`endor-estate`; not an agent skill)
- [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md)
- [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md)
