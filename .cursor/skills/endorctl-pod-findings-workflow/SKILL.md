---
name: endorctl-pod-findings-workflow
description: Enumerate namespaces, discover project tags, select projects by tag, and aggregate findings with endorctl filters for SCA/SAST/Secrets. Use when building pod/tag scoped reporting or validating UI-equivalent findings queries.
---
# Endorctl Pod Findings Workflow

## Purpose
Use this workflow to produce pod/tag scoped findings metrics with `endorctl` using API filters that match UI logic as closely as possible.

## Critical callouts
- **Fully qualified namespace:** use `tenant.parent.child` style names (example: `endor-solutions-tgowan.gh_personal`), not just child namespace short names.
- **Credentials/bootstrap:** run `endorctl init` to set up authentication. This initializes user config in the home directory at `~/.endorctl/config.yaml` (platform equivalent home path on Windows/macOS/Linux).
- **Default branch context:** use `context.type==CONTEXT_TYPE_MAIN`.
- **Finding severity field:** use `spec.level` in filters.

## Command sequence (shell-agnostic)

### 1) Enumerate namespaces (including descendants)
```text
endorctl api list --resource Namespace --traverse --list-all --field-mask meta.name,tenant_meta.namespace,uuid --output-type json
```

Build fully qualified names from:
- `tenant_meta.namespace + "." + meta.name`

### 2) List projects by tag in namespace scope
```text
endorctl api list --resource Project --namespace <fq-namespace> --filter 'meta.tags contains ["<tag>"]' --list-all --field-mask meta.name,meta.tags,uuid --output-type json
```

### 3) (Guardrail) Discover available tag values
Use grouped unique tags if supported:
```text
endorctl api list --resource Project --namespace <root-namespace> --traverse --group-unique-value-paths meta.tags --output-type json
```

If the grouped query errors in tenant backend, fallback:
```text
endorctl api list --resource Project --namespace <root-namespace> --traverse --list-all --field-mask meta.tags --output-type json
```
Then unique the `meta.tags` values client-side.

### 4) SCA filter (per project)
```text
endorctl api list --resource Finding --namespace <fq-namespace> --filter 'context.type==CONTEXT_TYPE_MAIN and spec.project_uuid==<project-uuid> and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY] and spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION] and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]' --count --output-type json
```

### 5) SAST filter (per project)
- FedRAMP style:
```text
endorctl api list --resource Finding --namespace <fq-namespace> --filter 'context.type==CONTEXT_TYPE_MAIN and spec.project_uuid==<project-uuid> and spec.finding_categories contains [FINDING_CATEGORY_SAST] and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]' --count --output-type json
```

- Commercial variants:
```text
... and spec.finding_tags contains [FINDING_TAGS_AI] ...
```
```text
... and spec.finding_tags contains [FINDING_TAGS_TRUE_POSITIVE] ...
```
```text
... and (spec.finding_tags contains [FINDING_TAGS_AI] or spec.finding_tags contains [FINDING_TAGS_TRUE_POSITIVE]) ...
```

### 6) Secrets filter (per project)
```text
endorctl api list --resource Finding --namespace <fq-namespace> --filter 'context.type==CONTEXT_TYPE_MAIN and spec.project_uuid==<project-uuid> and spec.finding_categories contains [FINDING_CATEGORY_SECRETS] and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_MEDIUM]' --count --output-type json
```

### 7) Optional dedupe (cross-pod/cross-project)
List finding UUIDs and dedupe client-side:
```text
endorctl api list --resource Finding --namespace <fq-namespace> --filter '<same-filter>' --list-all --field-mask uuid --output-type json
```

## Recommended execution pattern
1. Discover namespaces and normalize to fully qualified names.
2. Discover available tags (guardrail).
3. If input tag is missing, stop early and print valid tags.
4. Loop namespaces -> tagged projects.
5. For each project, run SCA/SAST/Secrets queries in `CONTEXT_TYPE_MAIN`.
6. Aggregate project rows to namespace and total summaries.
7. If running pod-scoped reports that overlap projects, optionally dedupe by finding UUID.
