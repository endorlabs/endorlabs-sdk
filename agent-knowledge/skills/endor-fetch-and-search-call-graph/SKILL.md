---
name: endor-fetch-and-search-call-graph
description: >-
  Fetch project call graph artifacts, decode zstd payloads into searchable node
  and edge files, and run safe intersection/path searches. Use when retrieving
  call graph data, checking whether symbols exist, and extracting node/edge/path
  facts for downstream reasoning.
endorlabs:
  catalog:
    workflow_id: callgraph-search
    cli: endor-callgraph-search
    module: endorlabs.workflows.callgraph.search
    default_output: stdout or caller path
    agent_visible: true
    composition: library_api
    library_entrypoints:
      - endorlabs.workflows.callgraph.run_callgraph_sweep
---

# Fetch and Search Call Graph

## Purpose

Turn raw call graph storage into **searchable, join-friendly JSON** (`decoded_callables.json`, `decoded_edges.json` when using `--decode-zstd`) and run **deterministic** node/edge/path queries. Use this skill when the task is symbol reachability, presence checks, or extracting graph facts for reasoning—not for listing scan findings (see [endor-retrieve-scan-results](retrieve-scan-results/SKILL.md)).

For full PV/finding reachability triage across customer and `oss` planes, prefer `uv run endor-reachability-context` first; use this skill as the graph-plane utility layer when you need focused symbol/path extraction from decoded artifacts.

## Ordering

1. **Credentials** — `uv run --env-file .env` (or equivalent) for `endorlabs.Client`.
2. **Fetch (choose one):**
   - **Context bundle (recommended)** — run [endor-project-agent-context](../endor-project-agent-context/SKILL.md) with **`--callgraph-sweep`** (`uv run endor-agent-context ...`). Use **`context_manifest.json`** `artifacts.callgraph_sweep` for paths to raw/decoded exports and the sweep manifest.
   - **Programmatic** — `endorlabs.tools.dependency_explorer.retrieve_call_graph_full` plus `decode_callgraph` (same primitives as `endorlabs.workflows.callgraph.sweep.run_callgraph_sweep`) when you need a one-off fetch outside the export CLI.
3. **Discover paths** — from `context_manifest.json` `artifacts.callgraph_sweep`, or from a sweep output directory’s `manifest.json`. Use a namespace consistent with the project’s `tenant_meta.namespace` when listing or resolving the project.
4. **Search** — `uv run endor-callgraph-search` (or `uv run python -m endorlabs.workflows.callgraph.search`) with `--callables`, `--edges`, and filter patterns.
5. **Reason** — join on method IDs; treat edges as static analysis facts, not proof of runtime execution.

## Why this skill exists

Raw call graph payloads are not directly search-friendly. Safe retrieval should
start from decoded files (`decoded_callables.json`, `decoded_edges.json`) and
use method IDs for joins, intersections, and path checks.

## Library and CLI entrypoints

- `endorlabs.workflows.callgraph.sweep.run_callgraph_sweep` — enumerates PVs and writes call graph exports (used by agent context `--callgraph-sweep`).
- `endorlabs.workflows.callgraph.decoded.decode_payload` — canonical decoded shape contract (`summary`, `callables`, `edges`) shared by sweep + reachability workflows.
- `endorlabs.workflows.callgraph.search` — searches decoded callables/edges (`endor-callgraph-search`).
- Bundle orchestration: `uv run endor-agent-context ... --callgraph-sweep` (see [endor-project-agent-context](../endor-project-agent-context/SKILL.md)).

## Inputs

- `tenant` — `endorlabs.Client` tenant / auth (same as other CLIs in this repo).
- `namespace` — list scope; **project resolution may use traverse**; when in doubt, use the project’s actual `tenant_meta.namespace`.
- `project` — 24-hex project UUID or project `meta.name` (e.g. repository URL) per script help.
- **Decode** — `--decode-zstd` when you need text JSON for search; otherwise you only have compressed or envelope payloads.
- **Search CLI** — paths to `--callables` and `--edges`, plus patterns accepted by `search_callgraph` (see script `--help`).

## Outputs

- A directory under `.endorlabs-context/workspace/projects/` (or `workspace/sessions/<user>/callgraph/` for ad-hoc sweeps) with `manifest.json` mapping artifact paths when using the sweep workflow. See [workspace-layout](../../rules/endor-workspace-layout.md).
- Decoded `decoded_*.json` when `--decode-zstd` is set.
- When using **project context export** with a sweep, **`context_manifest.json`** at the bundle root: read `artifacts.callgraph_sweep` to locate the sweep output (or `null` if the sweep was not run).

## Bounds

- Prefer capping list operations when extending this flow; the standalone fetch script and the export’s `--callgraph-max-pages` are there to limit `PackageVersion` enumeration. Do not assume full-tenant graph dumps.

## Multi-pass bundles (project-agent-context)

When the user ran `endor-agent-context` with **`--callgraph-sweep`** (Pass 3), **`context_manifest.json`** records `artifacts.callgraph_sweep` with export counts and list caps. **Read that object before** concluding “missing call graphs” — Pass 1 may list many PVs while Pass 2 only hydrated a subset unless `--hydrate-pv-uuids` / `--hydrate-top-n` was used.

**Progressive disclosure:** full pass/manifest rules live in [MULTIPASS_LLM_CONTRACT.md](../endor-project-agent-context/MULTIPASS_LLM_CONTRACT.md). Load it only when you need truncation/escalation semantics.

## Example workflow (standalone)

1. Fetch and decode:

```bash
uv run --env-file .env endor-agent-context \
  --tenant "<tenant>" \
  --namespace "<namespace>" \
  --project "<project-uuid-or-name>" \
  --output-dir .endorlabs-context/workspace/projects \
  --callgraph-sweep \
  --decode-zstd
```

2. Use `context_manifest.json` `artifacts.callgraph_sweep` (or the sweep folder `manifest.json`) to locate decoded files.

3. Search nodes/edges:

```bash
uv run endor-callgraph-search \
  --callables "<decoded_callables.json>" \
  --edges "<decoded_edges.json>" \
  --node-pattern "requests" \
  --source-pattern "myapp.billing.service" \
  --target-pattern "mypackage.http/request"
```

## Example use cases

- Verify whether function `A` reaches function `B`.
- List all nodes mentioning a package symbol (`requests`, `sqlalchemy`, etc.).
- Find edges where source and target belong to different subsystem patterns.
- Extract same-name target fanout for a given source function.

## Safety checks

- Prefer decoded artifacts over raw envelope JSON.
- Confirm both symbol existence and edge existence.
- Use method IDs for final joins, not URI text alone.
- Treat static graph edges as graph facts, not runtime execution proof.

## Documentation hops

- Deep reference: [CALL_GRAPH_FORMAT_AND_SEARCH.md](CALL_GRAPH_FORMAT_AND_SEARCH.md) in this skill directory.
- Platform docs: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)

## Reference

For file format mapping and robust search guidance, see
[CALL_GRAPH_FORMAT_AND_SEARCH.md](CALL_GRAPH_FORMAT_AND_SEARCH.md).
