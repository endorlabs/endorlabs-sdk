# Call Graph Format and Search

## Purpose

This guide explains:

- how fetched call graph artifacts are structured,
- how node/edge mapping works,
- how to search safely without missing results (including **multi-hop** paths).

It is intentionally implementation-focused and avoids customer-specific values.

## Artifact layout

After **`endor-agent-context --callgraph-export --decode-zstd`** (recommended) or an
equivalent export, each exported graph typically includes:

- `callgraph_export_manifest.json` (export directory)
- `NNNN_<pv_uuid>.call_graph.json` (raw payload)
- `NNNN_<pv_uuid>.decoded_summary.json`
- `NNNN_<pv_uuid>.decoded_callables.json`
- `NNNN_<pv_uuid>.decoded_edges.json`

Locate paths via bundle **`context_manifest.json`** → `artifacts.callgraph_export`, or the export folder `callgraph_export_manifest.json`.

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

## Path search protocol

Follow this order. **Do not stop after step 2 when the user asked for a “path” or “stitch”.**

### Step 1 — Existence

Confirm both symbols exist in `decoded_callables.json`:

```bash
uv run endor-callgraph-search \
  --callables "<decoded_callables.json>" \
  --edges "<decoded_edges.json>" \
  --node-pattern "<module>" \
  --node-pattern "<symbol_fragment>"
```

Or filter callables by URI substring before edge work.

### Step 2 — Direct edge (`endor-callgraph-search`)

```bash
uv run endor-callgraph-search \
  --callables "<decoded_callables.json>" \
  --edges "<decoded_edges.json>" \
  --source-pattern "<app>.<module>/<Type>.<method>" \
  --target-pattern "<dependency>/<symbol>" \
  --out "<workspace>/search_direct.json"
```

- `edge_hits_total > 0` → record `source_uri`, `target_uri`, `call_types`.
- `edge_hits_total == 0` → **continue to step 3** (common for wrapper methods).

### Step 3 — Transitive path (BFS on IDs)

When step 2 returns zero edges, use **`endor-callgraph-search`** path mode or `find_call_graph_path`:

```bash
uv run endor-callgraph-search \
  --callables "<decoded_callables.json>" \
  --edges "<decoded_edges.json>" \
  --path-from "<module>" \
  --path-from "<symbol_fragment>" \
  --path-to "<dependency>/<symbol>" \
  --max-depth 6 \
  --out "<workspace>/path_search.json"
```

Or live probe: `uv run endor-callgraph-path --tenant … --project … --path-from … --path-to …`.

Programmatic import: `endorlabs.workflows.callgraph.find_call_graph_path`.

When using path mode manually:

1. Resolve `method_id` for the **entry** symbol (e.g. public `get(` on a client type).
2. Resolve candidate **target** IDs (e.g. external `Client.request()`).
3. BFS over `decoded_edges.json` with a small max depth (4–6).
4. Output the **full URI chain**, not only first/last hop.

**Typical wrapper chain (Python HTTP clients):**

```text
<Type>.get(...)
  → <Type>._request(...)
    → <Type>._request_with_retry(...)
      → httpx._client/Client.request()
```

Searching only `get` → `httpx` as a **direct** edge often correctly returns **0**; the path still exists.

### Step 4 — Neighborhood context

If path is ambiguous, list immediate outbound neighbors of the source `method_id` before concluding “no path”.

### Step 5 — Collision check

If one source links to many same-name targets, record the fanout set (`possible_symbol_collision: true` in triage notes).

## Return type vs call target

URIs that mention a dependency in the **return type** (e.g. `.../APIClient.get(...)/httpx._models/Response`) are **not** the same as an edge into that library’s **callable** (e.g. `httpx._client/Client.request()`).

When stitching to a third-party API:

- Prefer targets with `/Client.request`, `/Client.get`, or similar **defined** externals.
- Do not treat “returns `Response`” as “calls `httpx`” without an edge into `Client.*`.

## Safe retrieval workflow (summary)

1. **Existence check** — both symbols in callables.
2. **Direct edge check** — `endor-callgraph-search` with source/target patterns.
3. **Path check** — `endor-callgraph-search --path-from` / `--path-to` or `find_call_graph_path` when direct edge is 0.
4. **Neighborhood check** — one-hop context.
5. **Collision check** — same-name fanout.

## Why grep can miss

Common pitfalls:

- Searching only raw `.call_graph.json` (compressed payload does not expose all symbols).
- Looking for dotted names when URIs use slash-separated path segments.
- Using one strict literal instead of multiple substring terms.
- Filtering only one file when the evidence is split across callables and edges.
- **Stopping at zero direct edges** on wrapped public methods.

## Robust matching tips

- Prefer multiple substring predicates over one exact literal.
  - Example: match `myapp`, `billing`, and `service`.
- Search callables first, then resolve edges by `method_id`.
- Keep source and target filters separate.
- For wrappers, search **inner** helpers (`_request_with_retry`) not only the public method name.
- Preserve intermediate outputs (`--out` JSON) for reproducibility.

## Example patterns

- Node discovery:
  - `--node-pattern "api_client"`
- Wrapper → library (when direct public→lib is 0):
  - `--source-pattern "<app>.api_client/<Type>._request_with_retry"`
  - `--target-pattern "httpx._client/Client.request"`
- Subsystem scope:
  - `--source-pattern "myapp.billing.service"`
- Directed intersection:
  - `--source-pattern "myapp.billing.service"`
  - `--target-pattern "mypackage.http/request"`

## Interpreting results

- `node_hits_total > 0` does not imply reachability by itself.
- `edge_hits_total > 0` indicates **direct** graph edges between filtered URI sets.
- `edge_hits_total == 0` does **not** rule out a multi-hop path — run path mode (BFS).
- A path in static graph data is graph-retrieval output; combine with separate reasoning for runtime claims.

## Programmatic path search

Prefer shipped primitives over session scripts:

```python
from endorlabs.workflows.callgraph import find_call_graph_path

result = find_call_graph_path(
    callables, edges,
    from_patterns=["APIClient", "get"],
    to_patterns=["Client.request"],
    max_depth=6,
)
```

Session-only glue may live under `.endorlabs-context/workspace/runs/scratch/` when no workflow covers the case.
