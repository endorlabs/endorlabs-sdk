# Multi-pass context retrieval — LLM behavior contract

Load this file **after** reading [SKILL.md](SKILL.md) when you need exact pass boundaries, manifest keys, or escalation wording.

## Pass model (single project)

| Pass | What runs | Primary artifact | Bounded by |
|------|-----------|------------------|------------|
| **1 — Index** | `PackageVersion.list` for the project | `package_versions_index.json` | `--pv-index-max-pages`, `--pv-index-page-size` |
| **2 — Hydrate** | `process_project` (BOM + optional CG pull + `DependencyMetadata`) | `bom_*.json`, `call_graph_*.json`, `dep_metadata.json`, `dependencies.json`, summary md | `--pv-limit`, `--dep-metadata-max-pages`, and list caps when using `--hydrate-pv-uuids` / `--hydrate-top-n` |
| **3 — Call-graph sweep** | Optional; enumerates PVs and exports call graph payloads | `callgraph_sweep/` + nested manifest | `--callgraph-max-pages`, `--callgraph-page-size` |

**Namespace graph (different skill):** [endor-map-project-dependency-relationships](../endor-map-project-dependency-relationships/SKILL.md) answers *cross-project* edges, not this per-repo bundle.

## Progressive disclosure — what to read first

1. **`context_manifest.json`** only (small): `version`, `subject`, `warnings`, `inventory`, `selection`, `hydration`, `artifacts`, `cli`.
2. **`package_versions_index.json`** when Pass 1 ran: triage PVs by name, `meta_update_time`, `call_graph_available`, `source_sha`.
3. **`dependency-callgraph-summary.md`** for human skim.
4. Large JSON (`dep_metadata.json`, BOMs, call graphs) only after targets are chosen.

## Manifest keys (contract)

- **`version`**: `2` for bundles that include `inventory` / `selection` / `hydration` sections (older bundles may be `1`).
- **`inventory`**: Pass 1. If `enabled` is false, Pass 1 was skipped (`--no-pv-index`). If `truncated` is true, the index hit list capacity — **do not** claim full PV coverage.
- **`selection`**: How Pass 2 chose PVs: `default_first_pv_limit`, `explicit_uuid_list`, or `top_n_by_meta_update_time`.
- **`hydration.pass_2_dependency_explorer`**: `skipped` true for `--index-only`; `missing_pv_uuids` if requested UUIDs were not in list results; `pv_list_truncated` if Pass 2 list cap may cut off data.
- **`artifacts.callgraph_sweep`**: Pass 3; `null` if not run. Object includes `pass`, `package_versions_total`, `call_graph_exports_total`, list caps.

## LLM rules — completeness and escalation

1. **Before** claiming “all package versions” or “no call graph,” read `warnings` and `inventory.truncated` / `hydration` / `callgraph_sweep` caps.
2. If `inventory.truncated`, `hydration.pv_list_truncated`, or `artifacts.dep_metadata_truncated` is true, say coverage is **bounded** and suggest raising the relevant `--*-max-pages` / `--*-page-size` (or `--dep-metadata-max-pages 0`) or using `--hydrate-pv-uuids` for known targets.
3. **Index-only** bundles (`hydration.pass_2_dependency_explorer.skipped`): no BOM/CG hydration — do not infer dependency or call-graph facts from missing files.
4. **Default Pass 2** without `--hydrate-pv-uuids` / `--hydrate-top-n` still uses **`--pv-limit`** (default 5) on the **legacy first page** of PVs — the **index** may list many more; reconcile with `selection.mode`.

## Example escalation prompts (for the user)

- “Index shows 80 PVs but `inventory.truncated` is true — increase `--pv-index-max-pages` / `--pv-index-page-size` and re-run.”
- “Hydrate only these UUIDs: …” → `--hydrate-pv-uuids <csv>`.
- “Newest 10 scans” → `--hydrate-top-n 10` (requires Pass 1 index).
- “Full call-graph exports for listed PVs” → `--callgraph-sweep` (Pass 3), optionally `--decode-zstd`.

## CLI quick reference

```text
Pass 1:  (default on) --pv-index-max-pages, --pv-index-page-size  |  --no-pv-index
Index only:  --index-only
Pass 2 selection:  --hydrate-pv-uuids a,b  |  --hydrate-top-n N
Pass 2 caps:  --pv-limit, --dep-metadata-max-pages, --pv-list-max-pages, --pv-list-page-size
Pass 3:  --callgraph-sweep, --callgraph-max-pages, --callgraph-page-size, --decode-zstd
```
