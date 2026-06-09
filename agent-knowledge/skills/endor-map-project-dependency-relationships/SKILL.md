---
name: endor-map-project-dependency-relationships
description: >-
  Walk all projects in a namespace, identify direct and indirect dependency
  relationships between projects via produced/consumed package versions, and
  emit a JSON relationship graph with evidence scoring.
endorlabs:
  catalog:
    workflow_id: relationships-map
    module: endorlabs.workflows.estate.analyze.project_map.map
    default_output: .endorlabs-context/workspace/projects/<uuid>/
    agent_visible: true
---

# Map Project Dependency Relationships

Build a namespace-wide project relationship graph by correlating:

- `PackageVersion` (producer side: project -> package version)
- `DependencyMetadata` (consumer side: project -> dependency package)

Return JSON artifacts only.

## What this skill does

1. Enumerates all projects in a namespace.
2. Builds producer edges from package versions.
3. Builds consumer edges from dependency metadata.
4. Joins producer and consumer edges by package coordinate.
5. Computes direct and indirect project-to-project relationships.
6. Writes JSON outputs with confidence/evidence details.

## CLI

- `python -m endorlabs.workflows.estate.analyze.project_map.map`
  - Namespace-wide relationship graph extractor.
  - Requires **`--tenant`** and **`--namespace`**. Lists `Project` and `PackageVersion` with `traverse=True` from the given namespace; lists `DependencyMetadata` per project filtered to `spec.importer_data.project_uuid` (when exposed on the model).
  - Writes:
    - `project_relationship_graph.json`
    - `project_relationship_paths.json`
    - `project_relationship_stats.json`

Example:

```bash
uv run --env-file .env python -m endorlabs.workflows.estate.analyze.project_map.map \
  --tenant "<endor_or_auth_tenant>" \
  --namespace "<tenant.namespace>" \
  --max-depth 3 \
  --output-dir .endorlabs-context/workspace/projects
```

## Purpose

For a **tenant/namespace** inventory of how repositories relate through package production and consumption, with bounded API usage. Not a substitute for single-project SBOM export (`uv run endor-agent-context`); use that when the subject is one repository’s dependency context and manifest.

## Cross-skill boundary (LLM)

This skill produces a **namespace-wide project graph** (three JSON files). It does **not** emit `context_manifest.json`, `package_versions_index.json`, or per-project BOM/call-graph hydration. For **one repository’s** multi-pass index → hydrate → sweep workflow, use [endor-project-agent-context](../endor-project-agent-context/SKILL.md) and, if needed, [MULTIPASS_LLM_CONTRACT.md](../endor-project-agent-context/MULTIPASS_LLM_CONTRACT.md) for manifest interpretation.
For per-PV/finding function reachability proof across customer + `oss` call graph planes, use `endor-reachability-context`; this skill remains topology-only and does not produce stitched vulnerable-function paths.

For an **estate-wide compile-dependency graph** (direct imports anchored on
`package_name`, `isolated` nodes, IR under
`.endorlabs-context/workspace/<slug>-<YYYYMMDD>/intermediate-representation/`), use
[endor-analytics-estate-dependencies](../endor-analytics-estate-dependencies/SKILL.md)
and [docs/estate/compile-graph.md](../../../docs/estate/compile-graph.md)
(`endor-estate pull` + `endor-estate analyze --only graph,viz`).

## Ordering

1. Set credentials (same as other SDK scripts). Confirm **`--namespace`** is the list root (often tenant root; `traverse=True` lists descendants).
2. Defaults are **unlimited** (`--max-pages 0`, `--dep-metadata-max-pages 0`). Watch stderr for truncation warnings; set a positive cap only when bounding cost is intentional.
3. Read the three JSON outputs; use [endor-project-agent-context](../endor-project-agent-context/SKILL.md) if you also need a single-project bundle the same session.

## Inputs

- `tenant` (required) — passed to `endorlabs.Client(tenant=...)`.
- `namespace` (required) — list root (traverse enabled in the script).
- `include_public` (optional, default: `false`) — if false, skip dependency rows marked public when that field is present.
- `max_depth` (optional, default: `3`) — indirect path discovery.
- `max_pages` (optional, default: `0`) — cap for `Project` and `PackageVersion` lists (`0` = unlimited).
- `page_size` (optional, default: `500`) — list page size.
- `dep_metadata_max_pages` (optional, default: `0`) — per-project cap for `DependencyMetadata.list` (`0` = unlimited).
- `output_dir` (optional, default: `.endorlabs-context/workspace/projects`).

## Outputs

Three JSON files under `output_dir` (see [JSON outputs](#json-outputs-required) below). Logging on stderr; no silent success requirement beyond file presence.

## Bounds

- `max_pages` / `dep_metadata_max_pages` prevent unbounded namespace-wide listing. Do not set these to “fetch everything” without explicit approval.
- Prefer the same `traverse=True` + namespace pattern documented here when listing from tenant root.

> **Agent note — empty edges vs truncation:** Producer-side matching uses a **bounded** `PackageVersion` list (`max_pages` × `page_size`). If `direct_project_edge_count` is **0**, distinguish (a) **no consumer `DependencyMetadata`** rows / no overlapping producer coordinates from (b) **truncated PV listing** where a producer never entered the capped window. Raise caps only with user approval. Tenant-wide context: [AGENTS.md](../../../AGENTS.md) (Agent notes — relationship map coverage).

## Documentation hops

- Local: `.endorlabs-context/platform/user-docs/`; API: OpenAPI in `.endorlabs-context/platform/openapi/openapiv2.swagger.json`.
- Online: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)

## Resource fields used

### Project

- `uuid`
- `meta.name`
- `tenant_meta.namespace`

### PackageVersion (producer evidence)

- `spec.project_uuid`
- `meta.name` (e.g. `npm://name@1.2.3`)
- `uuid`
- `tenant_meta.namespace`

### DependencyMetadata (consumer evidence)

- `spec.importer_data.project_uuid`
- `spec.importer_data.package_name`
- `spec.importer_data.package_version_name`
- `spec.dependency_data.package_name`
- `spec.dependency_data.resolved_version`
- `spec.dependency_data.unresolved_version`
- `spec.dependency_data.direct`
- `spec.dependency_data.public` (when present)
- `tenant_meta.namespace`

## Correlation model

Represent relationships as a graph over projects and package coordinates.

### 1) Producer index

Build:

- `produced_by[(package_name, version)] -> set[project_uuid]`
- `produced_name_only[package_name] -> set[project_uuid]`

Where `package_name`/`version` are parsed from `PackageVersion.meta.name`.

### 2) Consumer edges

For each dependency row:

- `consumer_project = spec.importer_data.project_uuid`
- `dep_name = spec.dependency_data.package_name`
- `dep_version = resolved_version or unresolved_version or ""`
- `is_direct = spec.dependency_data.direct`
- `is_public = spec.dependency_data.public` (if available)

Apply visibility filter:

- If `include_public=false`, ignore rows where `is_public is True`.

### 3) Join consumer -> producer

For each consumer edge, map to producer projects:

- Tier A exact: match `(dep_name, dep_version)` in `produced_by`
- Tier B name-only: if exact missing, match `dep_name` in `produced_name_only`

Create candidate project relation:

- `consumer_project -> producer_project`

Annotate each supporting package edge with:

- package name/version
- direct/transitive
- visibility
- evidence tier

### 4) Aggregate direct project edges

Collapse all package-level evidence into unique project edges.

Compute per edge:

- `support_count`
- `direct_support_count`
- `transitive_support_count`
- `private_support_count`
- `public_support_count`
- strongest evidence tier (`tier_a_exact` > `tier_b_name_only`)

### 5) Compute indirect paths

Using aggregated project edges, run bounded BFS up to `max_depth`.

For each `(source, target)` with path length >= 2, record:

- path nodes (project UUID sequence)
- hop count
- path confidence summary derived from constituent edge tiers

## JSON outputs (required)

Write these files under `output_dir`:

- `project_relationship_graph.json`
- `project_relationship_paths.json`
- `project_relationship_stats.json`

### `project_relationship_graph.json`

```json
{
  "namespace": "example.tenant",
  "generated_at": "2026-04-29T20:00:00Z",
  "projects": [
    {
      "uuid": "proj-a",
      "name": "https://github.com/org/a.git",
      "namespace": "example.tenant"
    }
  ],
  "edges": [
    {
      "from_project_uuid": "proj-consumer",
      "to_project_uuid": "proj-producer",
      "evidence_tier": "tier_a_exact",
      "support_count": 3,
      "direct_support_count": 1,
      "transitive_support_count": 2,
      "private_support_count": 3,
      "public_support_count": 0,
      "supporting_packages": [
        {
          "package_name": "npm://internal-lib",
          "package_version": "1.2.3",
          "dependency_kind": "direct",
          "visibility": "private",
          "evidence_tier": "tier_a_exact"
        }
      ]
    }
  ]
}
```

### `project_relationship_paths.json`

```json
{
  "namespace": "example.tenant",
  "max_depth": 3,
  "paths": [
    {
      "source_project_uuid": "proj-a",
      "target_project_uuid": "proj-c",
      "hop_count": 2,
      "path_project_uuids": ["proj-a", "proj-b", "proj-c"],
      "path_edge_tiers": ["tier_a_exact", "tier_b_name_only"],
      "confidence": "medium"
    }
  ]
}
```

### `project_relationship_stats.json`

```json
{
  "namespace": "example.tenant",
  "project_count": 42,
  "package_version_count": 300,
  "dependency_row_count": 12000,
  "direct_project_edge_count": 58,
  "indirect_path_count": 143,
  "tier_counts": {
    "tier_a_exact": 41,
    "tier_b_name_only": 17
  }
}
```

## Confidence rubric

- `high`: all edges in relation/path are `tier_a_exact`.
- `medium`: at least one `tier_a_exact`, remainder `tier_b_name_only`.
- `low`: only `tier_b_name_only` evidence.

## Required safeguards

- Deduplicate edges by `(consumer_project, producer_project, package_name, package_version)`.
- Exclude self-loop producer/consumer relations unless explicitly requested.
- Tolerate missing `resolved_version` by falling back to name-only evidence.
- Record ambiguous matches when multiple producers exist for same coordinate.

## Execution guidance

- Prefer `traverse=True` when listing from tenant root namespace.
- Use page limits to avoid unbounded calls.
- Persist raw intermediate datasets only when needed for debugging.
- Keep final deliverables JSON-only.
