---
name: endor-map-project-dependency-relationships
description: >-
  Live API namespace project graph: consumer DependencyMetadata joined to producer
  PackageVersion coordinates, with direct/indirect paths. Optional
  focus-producer-project-uuid for breaking-change consumer discovery. Not
  single-project SBOM export — use endor-project-retrieval-bundle.
endorlabs:
  catalog:
    workflow_id: relationships-map
    module: endorlabs.workflows.estate.analyze.project_map.map
    default_output: .endorlabs-context/workspace/
    agent_visible: true
---

# Map project dependency relationships

Namespace **consumer→producer** topology from produced/consumed package coordinates. Does **not** emit `context_manifest.json` or per-project BOM hydration.

## When to use

| Need | Tool |
|------|------|
| **Breaking change:** who consumes packages **my repo produces** | `--focus-producer-project-uuid <24-hex>` (below) |
| Full namespace graph (all project edges) | module CLI or `endor-estate analyze --only-relationships` without focus |
| Same graph into **estate workspace** IR | `uv run endor-estate analyze -n <estate_root> --only-relationships` ([endor-analytics-estate-dependencies](../endor-analytics-estate-dependencies/SKILL.md)) |
| **One repository** SBOM/DM/CG slice | [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) (`endor-agent-context`) — **not** relationship correlation |
| Compile-import graph | `endor-estate analyze --only graph,viz` |

## Breaking-change blast radius (narrow pull)

**Question:** “I changed an internal library in repo A — which other repos’ owners do I warn?”

1. Resolve **producer** project UUID for repo A (`Project.lookup` / export bundle `subject.project_uuid`).
2. Run relationship map with **`--focus-producer-project-uuid`** — still lists DependencyMetadata **across the namespace** (all potential consumers), but indexes producers **only from that project** and filters output edges to `to_project_uuid == <producer>`.

```bash
uv run --env-file .env python -m endorlabs.workflows.estate.analyze.project_map.map \
  --tenant "<tenant>" \
  --namespace "<tenant.namespace>" \
  --focus-producer-project-uuid "<producer_project_uuid>" \
  --output-dir .endorlabs-context/workspace/relationships
```

Or estate IR:

```bash
uv run endor-estate analyze -n <estate_root> --only-relationships \
  --focus-producer-project-uuid "<producer_project_uuid>"
```

**Read:** `project_relationship_graph.json` → `edges[]` where each edge is **consumer** (`from_project_uuid`) → **your repo** (`to_project_uuid`). Map `from_project_uuid` to `projects[].name` (repo URL) for owner notification. Use `project_relationship_paths.json` for indirect consumers up to `--max-depth`.

**Not project-scoped:** without `--focus-producer-project-uuid`, the pull is namespace-wide (all producers × all consumers). The retrieval bundle skill does **not** substitute — it has no cross-project join.

## Module CLI

```bash
uv run --env-file .env python -m endorlabs.workflows.estate.analyze.project_map.map \
  --tenant "<tenant>" \
  --namespace "<tenant.namespace>" \
  --max-depth 3 \
  --output-dir .endorlabs-context/workspace/relationships
```

Lists `Project` and `PackageVersion` with `traverse=True`; sharded per-project `DependencyMetadata` filtered by `spec.importer_data.project_uuid`.

**Writes:**

- `project_relationship_graph.json` — `focus_producer_project_uuid` when set; `edges` consumer→producer
- `project_relationship_paths.json` — indirect paths to the focus producer when set
- `project_relationship_stats.json`

## Inputs

- `tenant`, `namespace` (required)
- `focus_producer_project_uuid` (optional) — narrow to one producer project
- `include_public`, `max_depth`, `max_pages`, `dep_metadata_max_pages`, `page_size`, `max_workers`
- `output_dir` (default `.endorlabs-context/workspace/projects` in CLI; prefer `workspace/relationships/` or estate IR)

## Bounds

- Unlimited list caps by default; watch stderr for truncation.
- Focus mode still scans **all projects’** DependencyMetadata in the namespace — cost is not reduced to one project, only **output** is narrowed.
- Coordinate join only — not compile-time import graph.

## Documentation hops

- Local OpenAPI: `.endorlabs-context/platform/openapi/openapiv2.swagger.json`
- Online: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)
