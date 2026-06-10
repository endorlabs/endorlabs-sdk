---
name: endor-namespace-relationship-map
description: Live API namespace consumer→producer project graph from PackageVersion
  + DependencyMetadata coordinates; optional focus-producer-project-uuid for breaking-change
  blast radius. Namespace-scoped, not single-project SBOM — use endor-project-retrieval-bundle
  for one repo.
---

# Namespace relationship map

**Consumer→producer** edges between **projects** in a namespace (repos linked via internal package coordinates). Not a single-repo SBOM; not compile-import graph.

## Vocabulary

| Term | Meaning |
|------|---------|
| **`--tenant`** | Client auth tenant (e.g. platform root passed to `endorlabs.Client`). |
| **`--namespace`** | List root for traverse — **namespace scope** (tenant root or child). |
| **`--focus-producer-project-uuid`** | One **producer project** (repo) whose outgoing package edges you care about; filters **output**, not full namespace scan cost. |
| **Edge direction** | `from_project_uuid` = **consumer** repo → `to_project_uuid` = **producer** repo. |

## When to use

| Need | Tool |
|------|------|
| **Breaking change:** who consumes **my repo's packages** | `--focus-producer-project-uuid <24-hex>` |
| Full namespace graph (all edges) | module CLI or `endor-estate analyze --only-relationships` |
| Same JSON into workspace IR | [docs/estate/README.md](../../../docs/estate/README.md) — `endor-estate analyze --only-relationships` |
| **One repository** SBOM/DM/CG | [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) |
| Compile-import graph | `endor-estate analyze --only graph,viz` |

## Breaking-change blast radius

1. Resolve producer project UUID (repo A) — `Project.lookup` or retrieval bundle `subject.project_uuid`.
2. Run with **`--focus-producer-project-uuid`**.

```bash
uv run --env-file .env python -m endorlabs.workflows.estate.analyze.project_map.map \
  --tenant "<client_tenant>" \
  --namespace "<namespace_scope>" \
  --focus-producer-project-uuid "<producer_project_uuid>" \
  --output-dir .endorlabs-context/workspace/relationships
```

Or:

```bash
uv run endor-estate analyze -n <namespace_scope> --only-relationships \
  --focus-producer-project-uuid "<producer_project_uuid>"
```

**Read:** `project_relationship_graph.json` → `edges[]` — map `from_project_uuid` to `projects[].name` for owners to notify.

## Module CLI (full graph)

```bash
uv run --env-file .env python -m endorlabs.workflows.estate.analyze.project_map.map \
  --tenant "<client_tenant>" \
  --namespace "<namespace_scope>" \
  --max-depth 3 \
  --output-dir .endorlabs-context/workspace/relationships
```

**Writes:** `project_relationship_graph.json`, `project_relationship_paths.json`, `project_relationship_stats.json`.

## Inputs

- `tenant`, `namespace` (required)
- `focus_producer_project_uuid` (optional)
- `include_public`, `max_depth`, `max_pages`, `dep_metadata_max_pages`, `page_size`, `max_workers`

## Bounds

- Focus mode still scans DependencyMetadata for **all projects** in the namespace scope; only **output** is narrowed.
- Coordinate join — not compile-time import graph.

## Documentation hops

- OpenAPI: `.endorlabs-context/platform/openapi/openapiv2.swagger.json`
- Online: [https://docs.endorlabs.com/llms.txt](https://docs.endorlabs.com/llms.txt)
