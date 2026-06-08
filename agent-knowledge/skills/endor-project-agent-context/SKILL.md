---
name: endor-project-agent-context
description: >-
  Deterministic project context bundle: export context_manifest.json plus
  dependency explorer artifacts, optional call-graph sweep, multi-pass
  package-version index + targeted hydration, and composition with relationship
  mapping and call-graph search for remediation, threat, and repo-profiling agents.
endorlabs:
  catalog:
    workflow_id: agent-context
    cli: endor-agent-context
    module: endorlabs.workflows.agent_context.cli
    default_output: .endorlabs-context/workspace/projects/<uuid>/
    agent_visible: true
    composition: library_api
    library_entrypoints:
      - endorlabs.workflows.agent_context.build_context_manifest
      - endorlabs.workflows.agent_context.list_package_versions_for_index
---

# Project agent context (umbrella)

Read `context_manifest.json` before custom scripts; composition rules in [workflow-composition](../../rules/endor-workflow-composition.md).

## Purpose

Produce a **versioned, machine-readable context bundle** for a single project: `context_manifest.json` at the bundle root, plus `dependency_explorer` outputs (BOM slices, `dep_metadata.json`, `dependencies.json`, summary markdown) and optional call-graph export. Supports **multi-pass retrieval**: wide PV **index** → **hydration** (default or selected PVs) → optional **call-graph sweep**. This is the shared **retrieval layer** that remediation, threat-hunting, and repository-profiling agents consume before task-specific reasoning.

## Ordering

1. **Resolve credentials** — `uv run --env-file .env` (or equivalent) so `endorlabs.Client` can authenticate. Tenant-scoped; never paste secrets into skills or logs.
2. **Single-project context export** — run `uv run endor-agent-context` (or `uv run python -m endorlabs.workflows.agent_context.cli`) with `--tenant`, `--project`, optional `--namespace`, and `--output-dir` (default `.endorlabs-context/workspace/projects/`). **Done** means `context_manifest.json` exists and `artifacts` paths resolve on disk. If `--project` is a repo URL and resolution fails with **multiple matches**, pass **`--namespace`** for the intended child namespace or use the **24-hex project UUID** instead (same as `endorlabs.workflows.projects.resolve`). See [AGENTS.md](../../AGENTS.md) (Agent notes — ambiguous project URL).
3. **Read the manifest first (LLM)** — open only `context_manifest.json`, then follow progressive disclosure (see [MULTIPASS_LLM_CONTRACT.md](MULTIPASS_LLM_CONTRACT.md)).
4. **Namespace project graph** (different question) — for *cross-project* edges in a namespace, use `uv run python -m endorlabs.workflows.relationships.map` ([endor-map-project-dependency-relationships](map-project-dependency-relationships/SKILL.md)); not a substitute for the per-project bundle.
5. **Call graphs** — Pass 3: **`--callgraph-sweep`** on the export script, or standalone [endor-fetch-and-search-call-graph](fetch-and-search-call-graph/SKILL.md).
6. **Findings, scans, lineage** — [endor-retrieve-scan-results](retrieve-scan-results/SKILL.md), [endor-dependency-provenance](dependency-provenance/SKILL.md), [endor-dependency-finding-provenance](dependency-finding-provenance/SKILL.md).
7. **Reachability stitching** — run `uv run endor-reachability-context` with `--finding-uuid` or `--pv-uuid` and feed bundle outputs from this skill as source context when deeper function-level proof is needed.

## Multi-pass behavior (summary)

| Pass | Role | Default |
|------|------|---------|
| **1 — Index** | `package_versions_index.json` for triage (names, refs, `call_graph_available`, times) | **On**; disable with `--no-pv-index` |
| **2 — Hydrate** | BOM + CG + DependencyMetadata via `process_project` | **On** unless `--index-only` |
| **3 — Sweep** | Optional full PV call-graph export pass | `--callgraph-sweep` |

**LLM contract:** Always interpret `inventory`, `selection`, `hydration`, and `warnings` before claiming full coverage. Details: [MULTIPASS_LLM_CONTRACT.md](MULTIPASS_LLM_CONTRACT.md).

## Library and CLI entrypoints

| Step | Path |
|------|------|
| Project resolution | `endorlabs.workflows.projects.resolve` |
| Context export + manifest | `endorlabs.workflows.agent_context.export` / `endor-agent-context` |
| PV index helpers | `endorlabs.workflows.agent_context.package_versions` |
| Call-graph sweep (Pass 3) | `endorlabs.workflows.callgraph.sweep` (via export `--callgraph-sweep`) |
| Relationship map (namespace) | `python -m endorlabs.workflows.relationships.map` |
| Local search on decoded JSON | `endor-callgraph-search` / `python -m endorlabs.workflows.callgraph.search` |

## Inputs

- **Core:** `--tenant`, `--project`, optional `--namespace`, `--output-dir`.
- **Pass 1:** `--no-pv-index`, `--pv-index-max-pages`, `--pv-index-page-size`.
- **Pass 2:** `--index-only` (skip hydration), `--pv-limit`, `--dep-metadata-max-pages`, `--hydrate-pv-uuids`, `--hydrate-top-n`, `--pv-list-max-pages`, `--pv-list-page-size`.
- **Pass 3:** `--callgraph-sweep`, `--callgraph-max-pages`, `--callgraph-page-size`, `--decode-zstd`.
- **`--deterministic`** — stable ordering where applicable.

## Outputs

- **Bundle dir:** `<output_dir>/<slug>_<timestamp>/` with `context_manifest.json` (version **2** for new bundles), optional `package_versions_index.json`, dependency explorer files, optional `callgraph_sweep/`.
- **Stdout:** absolute path to `context_manifest.json` on success.

## Bounds

- **`--dep-metadata-max-pages`** defaults to **0 (unlimited)**; `context_manifest.json` sets
  `artifacts.dep_metadata_truncated` when a positive cap is hit.
- Pass 1 / Pass 3 PV list caps remain explicit (`--pv-index-max-pages`, `--callgraph-max-pages`).
  Raising caps increases API load and disk; ask the user before “fetch everything.”
- **`--pv-limit`** still caps how many PVs Pass 2 hydrates in **default** mode; the **index** can list more — see [MULTIPASS_LLM_CONTRACT.md](MULTIPASS_LLM_CONTRACT.md).

## Documentation hops

- **Deep:** [MULTIPASS_LLM_CONTRACT.md](MULTIPASS_LLM_CONTRACT.md) — manifest keys, escalation, progressive disclosure.
- Local: `.endorlabs-context/platform/user-docs/` after `endorlabs.init()` ([AGENTS.md](../../AGENTS.md)).
- Online: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)

## Linked skills

- [endor-retrieve-scan-results](retrieve-scan-results/SKILL.md) — findings, scan results, project lookup
- [endor-dependency-provenance](dependency-provenance/SKILL.md) — manifest / package introduction routes
- [endor-dependency-finding-provenance](dependency-finding-provenance/SKILL.md) — finding and SBOM lineages
- [endor-fetch-and-search-call-graph](fetch-and-search-call-graph/SKILL.md) — decode and search call graphs
- [endor-map-project-dependency-relationships](map-project-dependency-relationships/SKILL.md) — namespace project graph

## Personas (guidance only)

- **Remediation:** Bundle for repo facts; relationship map for cross-repo upgrade alignment.
- **Threat / reachability:** Pass 3 sweep or standalone fetch; read `artifacts.callgraph_sweep` in the manifest.
- **Profiling:** Manifest + summary + [endor-retrieve-scan-results](retrieve-scan-results/SKILL.md).
