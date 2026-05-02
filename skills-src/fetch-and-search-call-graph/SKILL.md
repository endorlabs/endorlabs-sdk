---
name: fetch-and-search-call-graph
description: >-
  Fetch project call graph artifacts, decode zstd payloads into searchable node
  and edge files, and run safe intersection/path searches. Use when retrieving
  call graph data, checking whether symbols exist, and extracting node/edge/path
  facts for downstream reasoning.
---

# Fetch and Search Call Graph

## Purpose

Turn raw call graph storage into **searchable, join-friendly JSON** (`decoded_callables.json`, `decoded_edges.json` when using `--decode-zstd`) and run **deterministic** node/edge/path queries. Use this skill when the task is symbol reachability, presence checks, or extracting graph facts for reasoning—not for listing scan findings (see [retrieve-scan-results](retrieve-scan-results/SKILL.md)).

## Ordering

1. **Credentials** — `uv run --env-file .env` (or equivalent) for `endorlabs.Client`.
2. **Fetch (choose one):**
   - **Standalone** — `scripts/callgraph/fetch_project_callgraph.py` with `--tenant`, `--namespace`, `--project`, and optional `--decode-zstd`. Use a namespace consistent with how the `Project` resource is stored: projects may live under a **child** `tenant_meta.namespace` while the CLI still accepts a **parent** namespace for listing in some tools; if results are empty, align `--namespace` with the project’s `tenant_meta.namespace` from the UI or API.
   - **Context bundle** — if you already ran [project-agent-context](project-agent-context/SKILL.md) with **`--callgraph-sweep`**, use **`context_manifest.json`** in the bundle: it lists artifact paths, including the call-graph sweep subfolder and (when used) a sweep manifest. You can skip a second `fetch_project_callgraph` when the manifest already points at decoded or raw exports you need.
3. **Discover paths** — open the `manifest.json` in the output directory (from `fetch_project_callgraph`) or the nested call-graph object under `context_manifest.json` `artifacts` when using the export workflow.
4. **Search** — `scripts/callgraph/search_callgraph.py` with paths to callables/edges and filter patterns.
5. **Reason** — join on method IDs; treat edges as static analysis facts, not proof of runtime execution.

## Why this skill exists

Raw call graph payloads are not directly search-friendly. Safe retrieval should
start from decoded files (`decoded_callables.json`, `decoded_edges.json`) and
use method IDs for joins, intersections, and path checks.

## Scripts and SDK entrypoints

- `scripts/callgraph/fetch_project_callgraph.py`
  - Fetches project call graph artifacts; optional `--decode-zstd` writes decoded node/edge files.
- `scripts/callgraph/search_callgraph.py`
  - Searches decoded callables and edges with deterministic filters.
- Optional related bundle: `scripts/agent_context/export_project_context.py` with `--callgraph-sweep` (see [project-agent-context](project-agent-context/SKILL.md)).

## Inputs

- `tenant` — `endorlabs.Client` tenant / auth (same as other CLIs in this repo).
- `namespace` — list scope; **project resolution may use traverse**; when in doubt, use the project’s actual `tenant_meta.namespace`.
- `project` — 24-hex project UUID or project `meta.name` (e.g. repository URL) per script help.
- **Decode** — `--decode-zstd` when you need text JSON for search; otherwise you only have compressed or envelope payloads.
- **Search CLI** — paths to `--callables` and `--edges`, plus patterns accepted by `search_callgraph` (see script `--help`).

## Outputs

- A directory (often under `.tmp/`) with `manifest.json` mapping artifact paths from `fetch_project_callgraph`.
- Decoded `decoded_*.json` when `--decode-zstd` is set.
- When using **project context export** with a sweep, **`context_manifest.json`** at the bundle root: read `artifacts.callgraph_sweep` to locate the sweep output (or `null` if the sweep was not run).

## Bounds

- Prefer capping list operations when extending this flow; the standalone fetch script and the export’s `--callgraph-max-pages` are there to limit `PackageVersion` enumeration. Do not assume full-tenant graph dumps.

## Multi-pass bundles (project-agent-context)

When the user ran `export_project_context.py` with **`--callgraph-sweep`** (Pass 3), **`context_manifest.json`** records `artifacts.callgraph_sweep` with export counts and list caps. **Read that object before** concluding “missing call graphs” — Pass 1 may list many PVs while Pass 2 only hydrated a subset unless `--hydrate-pv-uuids` / `--hydrate-top-n` was used.

**Progressive disclosure:** full pass/manifest rules live in [project-agent-context/MULTIPASS_LLM_CONTRACT.md](../project-agent-context/MULTIPASS_LLM_CONTRACT.md). Load it only when you need truncation/escalation semantics.

## Example workflow (standalone)

1. Fetch and decode:

```bash
uv run --env-file .env python scripts/callgraph/fetch_project_callgraph.py \
  --tenant "<tenant>" \
  --namespace "<namespace>" \
  --project "<project-uuid-or-name>" \
  --decode-zstd
```

2. Use the generated `manifest.json` to locate decoded files.

3. Search nodes/edges:

```bash
uv run --env-file .env python scripts/callgraph/search_callgraph.py \
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
