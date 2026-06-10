---
name: endor-analytics-estate-dependencies
description: 'Estate-scale workflows: pull workspace resources (project, dependency_metadata,
  finding, package_version), analyze version/risk cardinality and compile dependency
  graph from disk, unified dashboard viz. Use for estate-wide dependency diversity,
  risk-ranked cardinality, or CVE upgrade-path planning.'
---

# Estate dependency workflows

Unified CLI: **`endor-estate`** (`pull` | `analyze` | `summarize` | `export-version`).

Workspace: `.endorlabs-context/workspace/<slug>-<YYYYMMDD>/` with `data/collect_manifest.json`.

See [docs/estate/README.md](../../../docs/estate/README.md).

## Pull workspace

```bash
uv run --env-file .env endor-estate pull -n <estate_root>

uv run endor-estate pull -n <estate_root> \
  --workspace .endorlabs-context/workspace/<slug>-20260608 --resume
```

Collects all four resources: `project`, `dependency_metadata`, `finding`, `package_version`.

## Analyze (disk-first)

```bash
uv run endor-estate analyze -n <estate_root> \
  --workspace .endorlabs-context/workspace/<slug>-20260608

uv run endor-estate analyze -n <estate_root> --only risk,graph,viz --top-n 20

uv run endor-estate analyze -n <estate_root> --only-relationships
```

`--only-relationships` runs the live API project relationship map into `intermediate-representation/` (same JSON as [endor-map-project-dependency-relationships](../endor-map-project-dependency-relationships/SKILL.md)). Does not require a prior `pull`.

Outputs IR under `intermediate-representation/` and `viz/estate_dashboard.html`.

Programmatic:

```python
from endorlabs.workflows.estate import (
    analyze_workspace,
    collect_workspace,
    workspace_dir_for,
)
```

## Single-package version drill (live API)

```bash
uv run endor-estate export-version -n <estate_root> \
  --package-name-match jackson-databind \
  -o version_cardinality.csv
```

Or library: `export_version_cardinality_for_package_match`.

## Summarize

```bash
uv run endor-estate summarize -n <estate_root> \
  --workspace .endorlabs-context/workspace/<slug>-20260608
```

Docs: [workspace.md](../../../docs/estate/workspace.md). Legacy CLI/layout: [changelog.md](../../../docs/changelog.md) (**Unreleased → Breaking**).
