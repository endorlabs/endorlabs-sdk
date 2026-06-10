---
name: endor-estate-workspace
description: >-
  Namespace-scoped bulk workflows via endor-estate: pull JSONL workspace, disk-first
  analyze (cardinality, risk, compile graph, dashboard), summarize, export-version,
  and optional live relationship map into IR. --namespace is scope (tenant root or
  child), not single-project export — use endor-project-retrieval-bundle for one repo.
endorlabs:
  catalog:
    workflow_id: estate-workspace
    cli: endor-estate
    module: endorlabs.workflows.estate.cli.main
    default_output: .endorlabs-context/workspace/<slug>-<YYYYMMDD>/
    agent_visible: true
    composition: library_api
    library_entrypoints:
      - endorlabs.workflows.estate.collect_workspace
      - endorlabs.workflows.estate.analyze_workspace
      - endorlabs.workflows.estate.export_version_cardinality_for_package_match
      - endorlabs.workflows.estate.export_risk_ranked_version_cardinality
---

# Estate workspace (`endor-estate`)

Unified CLI: **`endor-estate`** (`pull` | `analyze` | `summarize` | `export-version`).

Workspace: `.endorlabs-context/workspace/<slug>-<YYYYMMDD>/` with `data/collect_manifest.json`.

See [docs/estate/README.md](../../../docs/estate/README.md).

## Vocabulary

| Term | Meaning |
|------|---------|
| **Client tenant** | Auth for `endorlabs.Client(tenant=…)` — platform tenant root (e.g. `endor`), not the same as namespace scope. |
| **Namespace scope** | Value for `-n` / `--namespace` on this CLI — **tenant root or any child namespace** you want to pull/analyze (e.g. `tenant.example` or `tenant.example.child`). |
| **Estate workspace** | This pull → analyze pattern; always **multi-project** under the namespace scope. |
| **Project** | One repo — use [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) (`endor-agent-context`), not `endor-estate pull` alone. |

## Pull workspace

```bash
uv run --env-file .env endor-estate pull -n <namespace_scope>

uv run endor-estate pull -n <namespace_scope> \
  --workspace .endorlabs-context/workspace/<slug>-20260608 --resume
```

Collects: `project`, `dependency_metadata`, `finding`, `package_version`.

## Analyze (disk-first)

```bash
uv run endor-estate analyze -n <namespace_scope> \
  --workspace .endorlabs-context/workspace/<slug>-20260608

uv run endor-estate analyze -n <namespace_scope> --only risk,graph,viz --top-n 20

uv run endor-estate analyze -n <namespace_scope> --only-relationships
```

`--only-relationships` runs the live API consumer→producer map into `intermediate-representation/` (same JSON as [endor-namespace-relationship-map](../endor-namespace-relationship-map/SKILL.md)). Optional **`--focus-producer-project-uuid`** for breaking-change blast radius. Does not require a prior `pull`.

Outputs IR under `intermediate-representation/` and `viz/estate_dashboard.html`.

```python
from endorlabs.workflows.estate import (
    analyze_workspace,
    collect_workspace,
    workspace_dir_for,
)
```

## Single-package version drill (live API)

```bash
uv run endor-estate export-version -n <namespace_scope> \
  --package-name-match jackson-databind \
  -o version_cardinality.csv
```

## Summarize

```bash
uv run endor-estate summarize -n <namespace_scope> \
  --workspace .endorlabs-context/workspace/<slug>-20260608
```

Related: [REMEDIATION.md](REMEDIATION.md). Docs: [workspace.md](../../../docs/estate/workspace.md).
