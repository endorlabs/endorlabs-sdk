# Analytics estate workflows

Tenant-scale reporting built on `DependencyMetadata` server-side aggregates and
tabular CSV export. Workflows live under `endorlabs.workflows.analytics`; they
compose the SDK client, namespace discovery helpers, and
`endorlabs.utils.tabular`.

## Entry points

| Surface | Purpose |
|---------|---------|
| `endor-analytics-export-deps` | CLI (`pyproject.toml` script) |
| `python -m endorlabs.workflows.analytics` | Same CLI module |
| `export_version_cardinality()` | Programmatic full-estate export |
| `export_version_cardinality_for_package_match()` | Single-package / filtered export |
| `analyze_intra_minor_remediation()` | Post-process usage rows for CVE planning |

## Layout

```
analytics/
  export_dependencies.py   # fetch, merge, rollup, CLI
  group_list.py            # grouped DependencyMetadata pagination
  namespaces.py            # estate namespace discovery
  remediation.py           # intra-minor flatten + CVE comparison helpers
  columns.py / types.py    # tabular presets and result types
  cli.py / __main__.py     # script entry
```

## Conventions

- **Namespace discovery:** `Namespace.list(traverse=True)` once per estate; counting
  queries use `traverse=False` on `DependencyMetadata`.
- **Wire path:** tenant namespace (`validate_namespace`), not the literal `oss`
  plane, for `DependencyMetadata` list/group operations.
- **Outputs:** CSV via `write_table` / `TabularExport`; JSON summary on stdout from
  the CLI.

## Agent guidance

For procedure, query-mode tradeoffs, and worked examples, use the
**analytics-estate-dependencies** skill in `skills-src/` (mirrored to
`.cursor/skills/`).

## Tests

```bash
uv run pytest tests/unit/workflows/analytics/ -q
```
