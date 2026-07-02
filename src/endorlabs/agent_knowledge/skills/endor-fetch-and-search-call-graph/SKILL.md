---
name: endor-fetch-and-search-call-graph
description: Fetch project call graph artifacts, decode zstd payloads into searchable
  node and edge files, and run safe direct-edge or multi-hop path searches on the
  customer PackageVersion plane. Use for static symbol paths (e.g. app code to a dependency
  API)—not for Finding/CVE reachability triage (hand off to endor-reachability-provenance),
  scan finding lists (endor-retrieve-scan-results), or natural-language function summaries
  (VectorStoreQuery; separate flow).
---

# Fetch and Search Call Graph

## Purpose

Turn raw call graph storage into **searchable, join-friendly JSON** (`decoded_callables.json`, `decoded_edges.json` when using `--decode-zstd`) and run **deterministic** node/edge/path queries on the **customer tenant graph** (keyed by `PackageVersion`).

Use this skill for **static call-graph facts**: symbol presence, direct edges, and **transitive** paths. Do not treat graph edges as proof of runtime execution.

## Plane gate (read first)

| User ask | Use | Do **not** use |
|----------|-----|----------------|
| “Does **our code** call **library X**?” (e.g. `APIClient` → `httpx`) | This skill | `VectorStoreQuery`, finding reachability |
| “Is the **vulnerable function** reachable for **this Finding**?” | `uv run endor-reachability-context` → [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) | Call-graph search alone |
| “List findings / scans for a project” | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | Call graph |
| “Semantic **function summary** / NL code search” | `client.VectorStore` + `VectorStoreQuery` (tenant store; scope by project `meta.name`) | `CallGraphData.decode` |

**Vocabulary:** **Call-graph reachability** = static edges in decoded JSON. **Finding reachability** = finding tags, `oss` vuln metadata, stitched customer + `oss` planes — different skill.

## Ordering (escalation ladder)

Do **not** skip to ad-hoc `CallGraphData.decode` on the first `PackageVersion` row.

1. **Credentials** — `uv run --env-file .env` (or equivalent) for `endorlabs.Client`.
2. **Fetch (required first)** — [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) with **`--callgraph-export`** and **`--decode-zstd`**:

   ```bash
   uv run --env-file .env endor-agent-context \
     --tenant "<tenant>" \
     --namespace "<namespace>" \
     --project "<project-uuid-or-name>" \
     --output-dir .endorlabs-context/workspace/projects \
     --callgraph-export \
     --decode-zstd
   ```

3. **Discover paths** — read **`context_manifest.json`** → `artifacts.callgraph_export`. Nested `callgraph_export/callgraph_export_manifest.json` lists decoded file paths.
4. **Reuse only when present** — if a prior bundle exists under `workspace/projects/`, read its manifest first; do not re-fetch unless stale or `force` requested.
5. **Single-PV spot-check (last resort)** — `client.CallGraphData.decode(package_version)` only after [PackageVersion selection](#packageversion-selection). See [facade-helpers.md](../../../docs/guides/facade-helpers.md).
6. **Search** — `uv run endor-callgraph-search` with `--callables`, `--edges`, and patterns; use `--path-from` / `--path-to` for multi-hop BFS. Follow [path search protocol](call-graph-format-and-search.md#path-search-protocol).
7. **Reason** — join on `method_id`; record direct edges **and** transitive chains when wrappers sit in between.

**Stop condition:** If `artifacts.callgraph_export` is null or every decode attempt returns `NotFoundError` for PVs tried within cap → report **“no CallGraphData for project”** with PV count tried. Do not fall back to tenant-wide unscoped search.

## PackageVersion selection

When using programmatic decode (step 5 above):

1. Resolve `Project` first; use **`namespace=project.namespace`** on `PackageVersion.list_by_project`.
2. Prefer PVs with **`spec.call_graph_available=true`**, ordered **`refs/heads/main` / `main` first**, then other `source_code_reference.ref` values.
3. Use `resolve_package_version_with_callgraph` or `build_callgraph_pv_inventory` — when no row has `call_graph_available`, the inventory **`message`** explains listed refs (do not guess).
4. Try `CallGraphData.decode(pv)` on ordered candidates; **`NotFoundError` → next PV**.
5. Record **`pv_uuid`**, **`source_ref`**, and **`pv_label`** in the output template.

Pass 3 of `endor-agent-context` records which PVs exported graphs in the export manifest — prefer those paths over guessing.

## Path search protocol

Thin wrappers (e.g. `get()` → `_request()` → `_request_with_retry()` → `httpx.Client.request()`) often yield **zero direct edges** between the user-named source and target. That is normal.

1. **Existence** — confirm both ends appear in `decoded_callables.json` (`--node-pattern` or grep URIs).
2. **Direct edge** — `endor-callgraph-search` with `--source-pattern` and `--target-pattern`.
3. **If `edge_hits_total` is 0** — run **`endor-callgraph-search --path-from … --path-to …`** or import `find_call_graph_path`. See [call-graph-format-and-search.md](call-graph-format-and-search.md#path-search-protocol).
4. **Distinguish** return-type nodes (`.../httpx._models/Response`) from **call targets** (`httpx._client/Client.request()`).
5. **Collision** — if one source fans out to many same-name targets, list the fanout set.

Example (portable patterns — substitute your module names):

```bash
# Path mode (BFS) when direct edges are 0
uv run endor-callgraph-search \
  --callables "<decoded_callables.json>" \
  --edges "<decoded_edges.json>" \
  --path-from "APIClient" \
  --path-from "get" \
  --path-to "Client.request" \
  --max-depth 6 \
  --out .endorlabs-context/workspace/sessions/<user>/callgraph/path.json

# Live probe (no bundle): endor-callgraph-path --tenant … --project … --path-from … --path-to …
```

## Why this skill exists

Raw call graph payloads are not directly search-friendly. Safe retrieval starts from decoded files and uses **method IDs** for joins. URI substring search alone misses multi-hop chains.

## Library and CLI entrypoints

- `endorlabs.workflows.callgraph.run_callgraph_export` — enumerates PVs and writes call graph exports (Pass 3 via `--callgraph-export`).
- `endorlabs.workflows.callgraph.find_call_graph_path` — BFS on decoded JSON.
- `endorlabs.workflows.callgraph.resolve_package_version_with_callgraph` — first decodable PV with `call_graph_available` (main ref first).
- `endorlabs.workflows.callgraph.build_callgraph_pv_inventory` — diagnostic when no call-graph PV exists for the project context.
- `client.CallGraphData.decode(package_version)` — decoded shape (`CallGraphDecoded`: `summary`, `callables`, `edges`, `envelope`).
- `endor-callgraph-search` — direct-edge and `--path-from` / `--path-to` search on local JSON.
- `endor-callgraph-path` — live project → decode → path search.
- `endor-vector-query` — list/probe/query tenant vector stores (separate from call-graph export).
- Bundle orchestration: `uv run endor-agent-context ... --callgraph-export` (see [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md)).

## Inputs

- `tenant` — `endorlabs.Client` tenant / auth.
- `namespace` — project list scope; use the project’s **`tenant_meta.namespace`** for PV lists and decode.
- `project` — 24-hex project UUID or `meta.name` (repo URL).
- **Decode** — `--decode-zstd` when you need text JSON for search.
- **Search CLI** — paths to `--callables` and `--edges`; repeatable patterns; `--path-from` / `--path-to` for BFS path mode.

## Outputs

- Directory under `.endorlabs-context/workspace/projects/` (bundle) or `workspace/sessions/<user>/callgraph/` (ad-hoc) with `callgraph_export_manifest.json` when using export.
- Decoded `decoded_*.json` when `--decode-zstd` is set.
- **`context_manifest.json`** at bundle root: `artifacts.callgraph_export` locates export output (`null` if Pass 3 was not run).

## Bounds

- Cap `PackageVersion` enumeration (`--callgraph-max-pages`, `--callgraph-page-size` on export). Do not assume full-tenant graph dumps.
- Pass 2 default `--pv-limit` may hydrate only a subset — read [multipass-llm-contract.md](../endor-project-retrieval-bundle/multipass-llm-contract.md) before inferring repo-wide posture from a partial bundle.

## Output template

Use this structure in the final result:

```markdown
## Call graph result

- Project: <uuid> namespace=<project.namespace>
- PV used: <uuid> <label> (or export manifest row)
- Source: <uri or search pattern>
- Target: <uri or search pattern>
- Direct edges: <n> (`edge_hits_total` or ID join)
- Transitive path: <full URI chain> or none within depth N
- Artifacts: <paths to decoded_callables.json, decoded_edges.json, search JSON>
- Ground truth (optional): <local file:line if repo checkout available>

## Notes

- Static graph only — not runtime execution proof.
- Finding/CVE reachability: hand off to endor-reachability-provenance if needed.
```

## Example use cases

- Verify whether function A reaches library B (including through private helpers).
- List nodes mentioning a dependency (`httpx`, `requests`, etc.).
- Find edges where source and target belong to different subsystem patterns.
- Extract same-name target fanout for one source symbol.

## Safety checks

- Prefer decoded artifacts over raw envelope JSON.
- Confirm symbol **existence** before claiming reachability.
- **Zero direct edges ≠ no path** — run BFS before concluding.
- Use method IDs for final joins, not URI text alone.
- Treat static graph edges as graph facts, not runtime execution proof.

## Related skills

| Skill | When |
|-------|------|
| [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) | **Required first** for `--callgraph-export` + manifest |
| [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) | Finding / `oss` vuln function reachability |
| [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) | Tenant-wide PRF approximation + PV error summary |
| [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | Finding rows, scan-scoped lists |
| [endor-dependency-provenance](../endor-dependency-provenance/SKILL.md) | Manifest path / ref lineage (not call paths) |

## Documentation hops

- Deep reference: [call-graph-format-and-search.md](call-graph-format-and-search.md)
- Facade helpers: [facade-helpers.md](../../../docs/guides/facade-helpers.md) (`CallGraphData.decode` / `.fetch`)
- Platform docs: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)
