---
name: endor-project-agent-context
description: >-
  Deterministic single-project retrieval bundle: context_manifest.json,
  dependency explorer artifacts, optional session summaries (findings/policies/
  versions), multi-pass PV index + hydration, and optional call-graph sweep.
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
---

# Project agent context (retrieval bundle)

Read `context_manifest.json` first; composition rules in [workflow-composition](../../rules/endor-workflow-composition.md).

## Purpose

Produce a **versioned, machine-readable retrieval bundle for one project** — not threat modeling, not namespace topology. The bundle is the shared **retrieval layer** agents consume before task-specific reasoning (remediation, profiling, reachability proof).

## Decision table

| Question | Use this skill | Hand off to |
|----------|----------------|-------------|
| SBOM slices, DependencyMetadata, PV index/hydration for **one repo** | `uv run endor-agent-context` | — |
| Findings/policies/repo-version **summaries in the same bundle** | add `--session-summaries` | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) for deeper scan RCA |
| Cross-project edges in a **namespace** | — | [endor-map-project-dependency-relationships](../endor-map-project-dependency-relationships/SKILL.md) or `endor-estate analyze --only-relationships` for estate workspace IR |
| Compile-import graph across an **estate** | — | [endor-analytics-estate-dependencies](../endor-analytics-estate-dependencies/SKILL.md) |
| Function-level call graph search | `--callgraph-sweep` or Pass 3 | [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) |
| Stitched vulnerable-function reachability | bundle as input context | `endor-reachability-context` |

## Ordering

1. **Credentials** — `uv run --env-file .env` (or equivalent). Never paste secrets into skills or logs.
2. **Export** — `uv run endor-agent-context` with `--tenant`, `--project`, optional `--namespace`, `--output-dir`. **Done** when `context_manifest.json` exists and `artifacts` paths resolve. Ambiguous repo URL → pass **`--namespace`** or **24-hex project UUID** ([AGENTS.md](../../../AGENTS.md#agent-notes)).
3. **Optional session layer** — `--session-summaries` writes `project-summary.md`, `findings/`, `policies/`, `repository-versions/` under the bundle; paths appear in `artifacts.session_summaries`.
4. **Read manifest (LLM)** — [MULTIPASS_LLM_CONTRACT.md](MULTIPASS_LLM_CONTRACT.md) for `inventory`, `selection`, `hydration`, `warnings`.
5. **Downstream** — scans/findings lineage, call-graph search, namespace graph, or reachability as the decision table indicates.

## Multi-pass behavior

| Pass | Role | Default |
|------|------|---------|
| **1 — Index** | `package_versions_index.json` | **On**; `--no-pv-index` to skip |
| **2 — Hydrate** | BOM + CG + DependencyMetadata | **On** unless `--index-only` |
| **3 — Sweep** | Full PV call-graph export | `--callgraph-sweep` |

## CLI entrypoints

| Step | Path |
|------|------|
| Export + manifest | `endor-agent-context` / `endorlabs.workflows.agent_context.export` |
| Session summaries | `--session-summaries` → `create_session` in `session_artifacts` |
| PV index helpers | `endorlabs.workflows.agent_context.package_versions` |
| Call-graph sweep | `--callgraph-sweep` → `endorlabs.workflows.callgraph.sweep` |

## Key flags

- **Core:** `--tenant`, `--project`, `--namespace`, `--output-dir`
- **Pass 1:** `--no-pv-index`, `--pv-index-max-pages`, `--pv-index-page-size`
- **Pass 2:** `--index-only`, `--pv-limit`, `--dep-metadata-max-pages`, `--hydrate-pv-uuids`, `--hydrate-top-n`
- **Pass 3:** `--callgraph-sweep`, `--callgraph-max-pages`, `--decode-zstd`
- **Session:** `--session-summaries`
- **`--deterministic`** — stable ordering for replay/diff

## Outputs

- **Bundle:** `<output_dir>/<slug>_<timestamp>/` with `context_manifest.json` (version **2**), optional `package_versions_index.json`, dependency explorer files, optional `callgraph_sweep/`, optional session subdir.
- **Stdout:** absolute path to `context_manifest.json`.

## Bounds

- **`--dep-metadata-max-pages`** defaults to **0 (unlimited)**; manifest sets `artifacts.dep_metadata_truncated` when capped.
- Pass 1 / Pass 3 list caps remain explicit; raising caps increases API load — ask before “fetch everything.”
- **`--pv-limit`** caps Pass 2 hydration in default mode; the index can list more ([MULTIPASS_LLM_CONTRACT.md](MULTIPASS_LLM_CONTRACT.md)).

## Linked skills

- [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md)
- [endor-dependency-finding-provenance](../endor-dependency-finding-provenance/SKILL.md)
- [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md)
- [endor-map-project-dependency-relationships](../endor-map-project-dependency-relationships/SKILL.md)
