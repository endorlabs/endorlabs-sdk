# Call Graph Format and Search

## Purpose

This guide explains:

- how fetched call graph artifacts are structured,
- how node/edge mapping works,
- how to search safely without missing results.

It is intentionally implementation-focused and avoids customer-specific values.

## Artifact layout

After running `fetch_project_callgraph.py --decode-zstd`, each exported graph
typically includes:

- `manifest.json`
- `NNNN_<pv_uuid>.call_graph.json` (raw payload)
- `NNNN_<pv_uuid>.decoded_summary.json`
- `NNNN_<pv_uuid>.decoded_callables.json`
- `NNNN_<pv_uuid>.decoded_edges.json`

## Data model

### 1) Nodes: `decoded_callables.json`

Flat array, one callable per row:

- `method_id` (integer, unique key)
- `uri` (symbol string)
- metadata fields (`access`, `first_line`, `last_line`, `defined`)

### 2) Edges: `decoded_edges.json`

Flat array, one edge per row:

- `source_id`
- `target_id`
- `source_uri` (convenience field)
- `target_uri` (convenience field)
- `call_types`
- `callsite_count`

### 3) Mapping

Use `method_id` as the source of truth:

- node lookup: `uri_by_id[method_id]`
- forward adjacency: `out_adj[source_id] -> [target_id...]`
- reverse adjacency: `in_adj[target_id] -> [source_id...]`

Text matching is useful for discovery, but final assertions should be based on
ID joins.

## Safe retrieval workflow

1. **Existence check**
   - Confirm both symbols exist in `decoded_callables.json`.
2. **Intersection check**
   - Check for direct edges between matched source IDs and target IDs.
3. **Path check**
   - If no direct edge, run BFS/DFS over IDs.
4. **Neighborhood check**
   - Inspect immediate inbound/outbound neighbors for context.
5. **Collision check**
   - If one source links to many same-name targets, record the fanout set for
     downstream interpretation.

## Why grep can miss

Common pitfalls:

- Searching only raw `.call_graph.json` (compressed payload does not expose all symbols).
- Looking for dotted names when URIs use slash-separated path segments.
- Using one strict literal instead of multiple substring terms.
- Filtering only one file when the evidence is split across callables and edges.

## Robust matching tips

- Prefer multiple substring predicates over one exact literal.
  - Example: match `myapp`, `billing`, and `service`.
- Search callables first, then resolve edges by `method_id`.
- Keep source and target filters separate.
- Preserve intermediate outputs in JSON for reproducibility.

## Example patterns

- Node discovery:
  - `--node-pattern "requests"`
- Subsystem scope:
  - `--source-pattern "myapp.billing.service"`
- Directed intersection:
  - `--source-pattern "myapp.billing.service"`
  - `--target-pattern "mypackage.http/request"`

## Interpreting results

- `node_hits_total > 0` does not imply reachability by itself.
- `edge_hits_total > 0` indicates direct graph edges between filtered sets.
- A path in static graph data is graph-retrieval output and should be combined
  with separate reasoning if runtime claims are needed.
