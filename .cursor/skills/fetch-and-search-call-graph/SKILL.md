---
name: fetch-and-search-call-graph
description: >-
  Fetch project call graph artifacts, decode zstd payloads into searchable node
  and edge files, and run safe intersection/path searches. Use when retrieving
  call graph data, checking whether symbols exist, and extracting node/edge/path
  facts for downstream reasoning.
---

# Fetch and Search Call Graph

## What this skill does

This skill gives a repeatable workflow to:

1. Fetch call graph data for a project.
2. Decode compressed graph payloads into explicit nodes and edges.
3. Search and intersect symbols safely.
4. Build path-focused retrieval artifacts.

## Why this skill exists

Raw call graph payloads are not directly search-friendly. Safe retrieval should
start from decoded files (`decoded_callables.json`, `decoded_edges.json`) and
use method IDs for joins, intersections, and path checks.

## Scripts

- `scripts/callgraph/fetch_project_callgraph.py`
  - Fetches project call graph artifacts.
  - Optional `--decode-zstd` writes decoded node/edge files.
- `scripts/callgraph/search_callgraph.py`
  - Searches decoded callables and edges with deterministic filters.

## Recommended workflow

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

## Reference

For file format mapping and robust search guidance, see
[CALL_GRAPH_FORMAT_AND_SEARCH.md](CALL_GRAPH_FORMAT_AND_SEARCH.md).
