---
name: endor-duplicate-projects
description: 'Find potential duplicate Projects across a tenant and all child namespaces:
  identical meta.name across namespaces, or names differing only when the user passes
  --name-strip-tokens (no default). Excludes SBOM projects (spec.sbom). Emit a flat
  CSV (project name, namespace, uuid, source) and a grouped canvas. Use when auditing
  project inventory or deduplicating registrations—not for findings, scan RCA, or
  single-project classification alone.'
---

# Duplicate project detection (tenant-wide)

List **potential duplicate** `Project` rows for a tenant (including **all child namespaces**). Output **must** include:

1. A **CSV file** with the exact column schema below (one row per project in a duplicate group).
2. A **Cursor canvas** grouping duplicate clusters for review.

For **CLI vs Cloud Scan** on each row, use [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md): `spec.git.external_installation_id` present → **`Cloud Scan`**; absent → **`CLI`**.

## Scope

**In scope**

- Tenant-wide `Project.list(traverse=True)` with bounded pagination.
- Duplicate heuristics: **exact name** across namespaces (default). Optional **canonical-name** clustering when the user supplies `--name-strip-tokens` (no default tokens).
- CSV + canvas deliverables with the fixed column schema.

**Out of scope**

- **SBOM projects** — skip any `Project` where **`spec.sbom`** is set (SBOM-only registrations are not duplicate candidates).
- Deleting or merging projects (report only).
- Finding-level or scan pipeline analysis → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md), [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md)
- CLI vs Cloud classification deep-dive → [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md)

## Duplicate rules

| Rule | Condition | Example |
|------|-----------|---------|
| **Exact name** | Same `meta.name` string on **2+** projects in **different** `tenant_meta.namespace` values | `github.com/org/repo` in `tenant.team-a` and `tenant.team-b` |
| **Canonical name (opt-in)** | Pass `--name-strip-tokens` with whole-word tokens to strip before comparing names (repeatable or comma-separated). **No default tokens** — without this flag, only exact-name clusters are emitted. | Customer example: `--name-strip-tokens mirror,shadow,clone` |

**Union clusters:** If project A matches B by exact name and B matches C by an opt-in canonical token, put A, B, C in one duplicate group. Only emit rows for projects that belong to a group with **≥ 2** members.

**SBOM exclusion:** Drop any project with **`spec.sbom`** before grouping or output. Do not include SBOM projects in CSV or canvas.

**Heuristic disclaimer:** Same repo URL registered twice is a strong duplicate signal; opt-in token stripping is a **customer naming convention** — review before merge/delete actions.

## CSV schema (required)

Write CSV with **exactly these six columns**, in this order, on every run:

| Column | Source field | Values |
|--------|--------------|--------|
| **`project name`** | `Project.meta.name` | Repository / project name string |
| **`namespace`** | `Project.tenant_meta.namespace` | Full namespace path |
| **`uuid`** | `Project.uuid` | Project UUID |
| **`source`** | Registration (`external_installation_id`) | **`CLI`** or **`Cloud Scan`** only |
| **`latest scan execution`** | Newest `ScanResult` `RunBySystem` | **`CLI`**, **`Cloud Scan`**, or **`unknown`** |
| **`mixed mode`** | Registration vs latest scan | **`true`** / **`false`** |

Header row (literal):

```text
project name,namespace,uuid,source,latest scan execution,mixed mode
```

**Do not** add extra columns (`duplicate_reason`, `group_id`, etc.) unless the user explicitly asks. Grouping belongs in the **canvas**, not the CSV.

**Registration mapping** (`source`):

```python
def project_source(project) -> str:
    git = project.spec.git if project.spec else None
    if git and git.external_installation_id:
        return "Cloud Scan"
    return "CLI"
```

**Latest scan execution:** bundled script uses `endorlabs.workflows.projects.inventory.fetch_latest_scan_execution_labels` (parallel `ScanResult.list_by_project` per duplicate row).

## Workflow

### Step 1: List all projects (tenant + children)

```python
import csv
import re
from collections import defaultdict
from pathlib import Path

import endorlabs

client = endorlabs.Client(tenant="<tenant>")

projects = list(
    client.Project.list_iter(
        traverse=True,
        mask="meta.name,tenant_meta.namespace,uuid,spec.git.external_installation_id,spec.sbom",
    )
)

projects = [
    p
    for p in projects
    if not client.Project.is_sbom(p)
]
```

Use `max_pages` when the user requests a bounded audit; otherwise paginate until exhausted.

> **Mask note:** With a non-empty mask, `list_iter` yields **`dict`** rows. Adapt field access: `row["meta"]["name"]`, `row.get("tenant_meta", {}).get("namespace")`, etc.

### Step 2: Build duplicate groups

**Default:** exact `meta.name` matches across **≥2** namespaces only.

**Opt-in canonical clustering:** when the user supplies naming tokens (for example
`mirror`, `shadow`, `clone`), pass them to the bundled script:

```bash
uv run python sdk/skills/endor-duplicate-projects/scripts/find_duplicate_projects.py \
  --tenant <tenant> --name-strip-tokens mirror,shadow,clone
```

SDK helpers for the `source` column: `client.Project.is_app(row)` → `Cloud Scan`, else `CLI`.

```python
from collections import defaultdict

# Exact-name groups (different namespaces only)
by_exact: dict[str, list] = defaultdict(list)
for p in projects:
    name = (p.get("meta") or {}).get("name") or ""
    by_exact[name].append(p)

exact_groups = [
    group
    for group in by_exact.values()
    if len({(r.get("tenant_meta") or {}).get("namespace") for r in group}) >= 2
]

# Optional: canonical groups only when strip_tokens is provided by the user
# (bundled script: --name-strip-tokens mirror,shadow,clone)
```

Merge overlapping groups (same UUID appearing in multiple candidate groups) before emitting rows.

### Step 3: Write CSV

Default path: `.endorlabs-context/workspace/sessions/<user>/exports/duplicate-projects.csv`

```python
output = Path(".endorlabs-context/workspace/sessions/<user>/exports/duplicate-projects.csv")
output.parent.mkdir(parents=True, exist_ok=True)

fieldnames = [
    "project name",
    "namespace",
    "uuid",
    "source",
    "latest scan execution",
    "mixed mode",
]
rows = [row_fields(p) for cluster in merged_clusters for p in cluster]
rows.sort(key=lambda r: (r["project name"].lower(), r["namespace"]))

with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
```

Or run the bundled helper:

```bash
uv run python .endorlabs-context/sdk/skills/endor-duplicate-projects/scripts/find_duplicate_projects.py \
  --tenant <tenant> \
  --output .endorlabs-context/workspace/sessions/<user>/exports/duplicate-projects.csv
```

### Step 4: Canvas (required when duplicates exist)

When **≥ 1 duplicate cluster** is found, create a Cursor canvas (see [canvas skill](https://docs.cursor.com)) with:

- **Summary:** tenant, total projects scanned, duplicate cluster count, row count.
- **Grouped sections:** one block per duplicate cluster; table columns match CSV: **project name**, **namespace**, **uuid**, **source**, **latest scan execution**, **mixed mode**.
- **No empty canvas:** if there are zero duplicate clusters, skip the canvas and report “no duplicates found” in chat only.

Embed the CSV row data inline in the canvas component (no `fetch()`).

## Output checklist

Before finishing, confirm:

- [ ] CSV exists with header `project name,namespace,uuid,source,latest scan execution,mixed mode`
- [ ] Every data row has **`source`** ∈ {`CLI`, `Cloud Scan`}
- [ ] Report duplicate-row registration vs latest-scan counts in chat summary
- [ ] SBOM projects (`spec.sbom` set) excluded from scan and output
- [ ] Only projects in multi-member duplicate groups are included
- [ ] Canvas groups the same rows visually (when duplicates exist)
- [ ] Artifacts under `.endorlabs-context/workspace/sessions/<user>/` (gitignored)

## When to use this skill vs others

| Goal | Skill |
|------|-------|
| Find cross-namespace duplicate registrations | **This skill** |
| Classify one project CLI vs Cloud | [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md) |
| Resolve which duplicate row to use for findings | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| Namespace consumer→producer graph | [endor-namespace-relationship-map](../endor-namespace-relationship-map/SKILL.md) |

## Related skills

| Need | Skill |
| ---- | ----- |
| CLI vs Cloud Scan source column | [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md) |
| Findings for a chosen project row | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| SDK list / traverse errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |
