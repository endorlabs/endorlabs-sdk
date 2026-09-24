---
name: endor-sbom-management
description: 'Use when importing CycloneDX/SPDX SBOMs via endorctl, checking file-vs-project

  coverage, listing ImportedSBOM rows, or exporting SBOM/VEX through Client

  facades (SBOMExport / VEXExport / AsyncJob). Coverage is baked into the import

  playbook. Not for estate-wide bulk pull, monorepo bom.Scan reimplementation,

  or SCA finding lineage (use endor-sca-findings).

  '
---

# SBOM management (import, coverage, export)

Manage software bill of materials through the proven **endorctl import + scan**
path, Client facades for inventory/export, and a **coverage check** that compares
file components to PackageVersions on the SBOM project.

## Scope

**In scope**

- Import CycloneDX JSON/XML or SPDX JSON with `endorctl sbom import` (or
  `endor-sbom import`)
- Post-import / standalone coverage: file `components[]` (+ metadata component)
  vs unique `PackageVersion.meta.name` via `list_by_project`
- List/get `ImportedSBOM`; create-only `SBOMExport` / `VEXExport`; poll `AsyncJob`
- Schema hygiene: valid PackageURL types, no unofficial `cdx:` property squat

**Out of scope**

- Estate-wide `endor-estate pull`
- Replacing endorctl's local `bom.Scan` with a pure-Python import pipeline
- Vulnerability lineage / finding triage → [endor-sca-findings](../endor-sca-findings/SKILL.md)
- Auth / credentials → [endor-auth-setup](../endor-auth-setup/SKILL.md)

## Formats and generators

Endor Labs supports **CycloneDX JSON**, **CycloneDX XML**, and **SPDX JSON**.

| Generator | Proven import path (scratch matrix) |
|-----------|--------------------------------------|
| cdxgen | CycloneDX JSON |
| Syft | SPDX JSON (SPDX-2.3) |

Syft CycloneDX and cdxgen SPDX-3 outputs may be rejected by `endorctl sbom import`
— prefer the proven pairs above for automation.

## Schema hygiene

- Identity join key is component **purl** → Endor name (`npm://…`, `pypi://…`, …)
- Unknown / odd purl types often land as `sbom://…` (weaker OSS matching)
- Do **not** invent reserved `cdx:` property names (e.g. `cdx:vcs:hash`)
- Hashes and VCS properties are **not** the vuln join key

## CLI

```bash
# Import (triggers endorctl ingest+scan)
uv run --env-file .env endor-sbom import -n <tenant> --sbom /path/to/bom.json --with-coverage

# Coverage only (after you already have project UUID)
uv run --env-file .env endor-sbom coverage -n <tenant> \
  --sbom /path/to/bom.json --project-uuid <project-uuid>

# List imports
uv run --env-file .env endor-sbom list-imports -n <tenant>

# Export via API facade
uv run --env-file .env endor-sbom export -n <tenant> \
  --kind sbom --parent-kind PackageVersion --parent-uuid <pv-uuid>
```

Default artifacts:

`.endorlabs/tasks/<slug>-<YYYY-MM-DD>/sbom/`

(`coverage_result.json`, `import_result.json`, `export_result.json`, `list_imports.json`)

## Library

```python
from endorlabs.workflows.sbom import run_coverage, run_import, run_sbom_export

result = run_import(namespace="<tenant>", sbom_path=path, run_coverage_after=True, client=client)
cov = run_coverage(client, sbom_path=path, project_uuid="<project-uuid>")
export = run_sbom_export(
    client,
    parent_kind="PackageVersion",
    parent_uuid="<pv-uuid>",
)
```

Facades:

```python
imports = client.ImportedSBOM.list()
row = client.ImportedSBOM.get(imports[0])
project_uuid = row.linked_project_uuid()
```

Prefer **`endorctl sbom import`** / `run_import` for ingest+scan. API
`ImportedSBOM.create` may store raw content without the CLI scan path.

## Related skills

| Need | Skill |
|------|-------|
| Finding / dependency lineage after import | [endor-sca-findings](../endor-sca-findings/SKILL.md) |
| `Project.is_sbom` / onboarding presence | [endor-config-presence](../endor-config-presence/SKILL.md) |
| Credentials | [endor-auth-setup](../endor-auth-setup/SKILL.md) |

## Rules

- [endor-namespace-scoping](../../rules/endor-namespace-scoping.md) — resolve Project, then `namespace=project.namespace` / `list_by_project`
- [endor-list-query-performance](../../rules/endor-list-query-performance.md) — no tiny `page_size`; selective filters
- [endor-portable-examples](../../rules/endor-portable-examples.md) — placeholders only in tracked content
- [endor-workflow-composition](../../rules/endor-workflow-composition.md) — library has no `print`; CLI owns artifacts
