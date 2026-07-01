---
name: endor-duplicate-projects
description: >-
  Find potential duplicate Projects across a tenant and all child namespaces:
  identical meta.name across namespaces, or names differing only by mirror/shadow/clone
  tokens. Excludes SBOM projects (spec.sbom). Emit a flat CSV (project name,
  namespace, uuid, source) and a grouped canvas. Use when auditing project inventory
  or deduplicating registrations—not for findings, scan RCA, or single-project
  classification alone.
---

# Duplicate project detection (tenant-wide)

List **potential duplicate** `Project` rows for a tenant (including **all child namespaces**). Output **must** include:

1. A **CSV file** with the exact column schema below (one row per project in a duplicate group).
2. A **Cursor canvas** grouping duplicate clusters for review.

For **CLI vs Cloud Scan** on each row, use [endor-cli-vs-cloud-projects](../endor-cli-vs-cloud-projects/SKILL.md): `spec.git.external_installation_id` present → **`Cloud Scan`**; absent → **`CLI`**.

## Scope

**In scope**

- Tenant-wide `Project.list(traverse=True)` with bounded pagination.
- Duplicate heuristics: **exact name** and **mirror/shadow/clone** variants.
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
| **Mirror / shadow / clone** | Names match after removing whole-word tokens **`mirror`**, **`shadow`**, or **`clone`** (case-insensitive; separators `-`, `_`, `.`, `/` around the token) | `github.com/org/repo` ↔ `github.com/org/repo-mirror` |

**Union clusters:** If project A matches B by exact name and B matches C by mirror token, put A, B, C in one duplicate group. Only emit rows for projects that belong to a group with **≥ 2** members.

**SBOM exclusion:** Drop any project with **`spec.sbom`** before grouping or output. Do not include SBOM projects in CSV or canvas.

**Heuristic disclaimer:** Same repo URL registered twice is a strong duplicate signal; mirror/shadow/clone naming is a **naming convention heuristic** — review before merge/delete actions.

## CSV schema (required)

Write CSV with **exactly these four columns**, in this order, on every run:

| Column | Source field | Values |
|--------|--------------|--------|
| **`project name`** | `Project.meta.name` | Repository / project name string |
| **`namespace`** | `Project.tenant_meta.namespace` | Full namespace path |
| **`uuid`** | `Project.uuid` | Project UUID |
| **`source`** | `Project.spec.git.external_installation_id` | **`CLI`** or **`Cloud Scan`** only |

Header row (literal):

```text
project name,namespace,uuid,source
```

**Do not** add extra columns (`duplicate_reason`, `group_id`, etc.) unless the user explicitly asks. Grouping belongs in the **canvas**, not the CSV.

**Source mapping:**

```python
def project_source(project) -> str:
    git = project.spec.git if project.spec else None
    if git and git.external_installation_id:
        return "Cloud Scan"
    return "CLI"
```

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

def is_sbom_project(row) -> bool:
    return (row.get("spec") or {}).get("sbom") is not None

projects = [p for p in projects if not is_sbom_project(p)]
```

Use `max_pages` when the user requests a bounded audit; otherwise paginate until exhausted.

> **Mask note:** With a non-empty mask, `list_iter` yields **`dict`** rows. Adapt field access: `row["meta"]["name"]`, `row.get("tenant_meta", {}).get("namespace")`, etc.

### Step 2: Build duplicate groups

```python
MIRROR_TOKEN = re.compile(
    r"[-_./]?(mirror|shadow|clone)[-_./]?",
    re.IGNORECASE,
)


def canonical_name(name: str) -> str:
    return MIRROR_TOKEN.sub("", (name or "").strip().lower())


def project_source_from_row(row) -> str:
    inst = (
        (row.get("spec") or {})
        .get("git", {})
        .get("external_installation_id")
    )
    return "Cloud Scan" if inst else "CLI"


def row_fields(row) -> dict:
    return {
        "project name": (row.get("meta") or {}).get("name") or "",
        "namespace": (row.get("tenant_meta") or {}).get("namespace") or "",
        "uuid": row.get("uuid") or "",
        "source": project_source_from_row(row),
    }


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

# Mirror/shadow/clone groups
by_canonical: dict[str, list] = defaultdict(list)
for p in projects:
    name = (p.get("meta") or {}).get("name") or ""
    by_canonical[canonical_name(name)].append(p)

mirror_groups = [
    group
    for group in by_canonical.values()
    if len(group) >= 2 and canonical_name((group[0].get("meta") or {}).get("name") or "")
]

# Union-find or simple uuid merge of group members into clusters
# (implement merge so overlapping groups become one cluster)
```

Merge overlapping groups (same UUID appearing in multiple candidate groups) before emitting rows.

### Step 3: Write CSV

Default path: `.endorlabs-context/workspace/sessions/<user>/exports/duplicate-projects.csv`

```python
output = Path(".endorlabs-context/workspace/sessions/<user>/exports/duplicate-projects.csv")
output.parent.mkdir(parents=True, exist_ok=True)

fieldnames = ["project name", "namespace", "uuid", "source"]
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
- **Grouped sections:** one block per duplicate cluster; table columns match CSV: **project name**, **namespace**, **uuid**, **source**.
- **No empty canvas:** if there are zero duplicate clusters, skip the canvas and report “no duplicates found” in chat only.

Embed the CSV row data inline in the canvas component (no `fetch()`).

## Output checklist

Before finishing, confirm:

- [ ] CSV exists with header `project name,namespace,uuid,source`
- [ ] Every data row has **`source`** ∈ {`CLI`, `Cloud Scan`}
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
