---
name: endor-map-project-dependency-relationships
description: >-
  Live API namespace project graph: producer PackageVersion + consumer
  DependencyMetadata joined by coordinate, with direct/indirect paths and
  evidence tiers. JSON only — not single-project SBOM export.
endorlabs:
  catalog:
    workflow_id: relationships-map
    module: endorlabs.workflows.estate.analyze.project_map.map
    default_output: .endorlabs-context/workspace/projects/
    agent_visible: true
---

# Map project dependency relationships

Namespace-wide **project-to-project topology** from produced/consumed package coordinates. Does **not** emit `context_manifest.json` or per-project BOM/call-graph hydration.

## When to use

| Need | Tool |
|------|------|
| Ad hoc graph under `workspace/projects/` | This skill's module CLI (below) |
| Same graph into an **estate workspace** IR tree | `uv run endor-estate analyze -n <estate_root> --only-relationships` ([endor-analytics-estate-dependencies](../endor-analytics-estate-dependencies/SKILL.md)) |
| **One repository** dependency context | [endor-project-agent-context](../endor-project-agent-context/SKILL.md) (`endor-agent-context`) |
| Compile-import graph (not PV coordinate join) | `endor-estate analyze --only graph,viz` — [docs/estate/compile-graph.md](../../../docs/estate/compile-graph.md) |
| Function reachability / stitched paths | `endor-reachability-context` (not topology-only) |

## Module CLI

```bash
uv run --env-file .env python -m endorlabs.workflows.estate.analyze.project_map.map \
  --tenant "<tenant>" \
  --namespace "<tenant.namespace>" \
  --max-depth 3 \
  --output-dir .endorlabs-context/workspace/projects
```

**Requires:** `--tenant`, `--namespace`. Lists `Project` and `PackageVersion` with `traverse=True`; sharded per-project `DependencyMetadata` with `spec.importer_data.project_uuid` filter.

**Writes (three JSON files):**

- `project_relationship_graph.json` — projects + direct edges with evidence
- `project_relationship_paths.json` — bounded indirect paths (`--max-depth`, default 3)
- `project_relationship_stats.json` — counts and tier summary

## Estate analysis layer

For large estates, prefer writing into the pulled workspace IR (same JSON filenames under `intermediate-representation/`):

```bash
uv run endor-estate analyze -n <estate_root> --only-relationships
# equivalent: --only relationships
```

Live API — does **not** require `endor-estate pull` first, but composes cleanly with pull + other analyze steps on the same workspace.

## Inputs (module CLI)

- `tenant`, `namespace` (required)
- `include_public` (default skip public rows)
- `max_depth` (default 3), `max_pages` / `dep_metadata_max_pages` (0 = unlimited)
- `page_size` (default 500), `max_workers` (default 16)
- `output_dir` (default `.endorlabs-context/workspace/projects`)

## Bounds

- Defaults are **unlimited** list caps; watch stderr for truncation warnings.
- **Empty edges:** distinguish no overlapping coordinates from **truncated** `PackageVersion` listing before raising caps ([AGENTS.md](../../../AGENTS.md#agent-notes)).
- Per-PV coordinate join only — not compile-time import graph.

## Correlation (summary)

1. Index producers from `PackageVersion.meta.name` → `(package, version)` and name-only tiers.
2. Join consumer `DependencyMetadata` rows (exact coordinate, then name-only fallback).
3. Aggregate project edges; BFS indirect paths up to `max_depth`.
4. Confidence: all `tier_a_exact` → high; mixed → medium; name-only → low.

Full field list and JSON shapes: module source `endorlabs.workflows.estate.analyze.project_map` and prior skill revision in git history if needed.

## Documentation hops

- Local OpenAPI: `.endorlabs-context/platform/openapi/openapiv2.swagger.json`
- Online: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)
