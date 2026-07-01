---
name: endor-cli-vs-cloud-projects
description: >-
  Classify Projects as CLI-scanned (local endorctl) vs Cloud-scanned (agentless
  SCM integrations such as GitHub or Bitbucket apps) using
  spec.git.external_installation_id. Tenant-wide runs emit a CSV with installation
  names resolved from Installation rows. Use when scan behavior, automation, or RCA
  depends on how the project was registered—not for listing findings or scan
  pipeline diffs (hand off to sibling skills).
---

# CLI vs Cloud project classification

**Cloud** projects are registered through Endor Labs **SCM integrations** (GitHub app, Bitbucket app, Azure DevOps, and similar). Scans are **agentless** — Endor Labs pulls source from the connected installation without a local `endorctl scan` on customer infrastructure.

**CLI** projects are created and scanned via **`endorctl`** (or API ingestion from local/CI runs). They do **not** carry an SCM app installation id on the `Project` row.

## Scope

**In scope**

- Tenant-wide or single-project classification via the bundled script.
- Resolve **`spec.git.external_installation_id`** on each `Project` row.
- Resolve the human-readable **`Installation.meta.name`** (with `spec.login` when needed) by matching `Installation.spec.external_id` to the project installation id.
- Emit the standard CSV on every run and summarize results in chat.

**Out of scope**

- Listing or triaging **Finding** rows → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- Scan pipeline regressions, logs, aggregate diffs → [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md)
- SSO / installation credential setup → [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md)

## Classification rule

| `spec.git.external_installation_id` | Classification | CSV `source` |
|-------------------------------------|----------------|--------------|
| **Present** (non-empty string) | **Cloud** | `Cloud Scan` |
| **Absent** / `null` | **CLI** | `CLI` |

Match `external_installation_id` to **`Installation.spec.external_id`** (tenant-wide `Installation.list(traverse=True)`). Use **`Installation.meta.name`** for the CSV `installation name` column; when `spec.login` is also set, format as `meta.name (login)` for disambiguation (common for multiple Azure installations).

**Related signals (Cloud only):**

| Field | Meaning |
|-------|---------|
| `spec.git.invalid_installation` | SCM installation was removed; Endor cannot refresh or rescan this Cloud project |
| `spec.git.http_clone_url` | May be set on Cloud projects for clone during agentless scan |

Do **not** infer Cloud vs CLI from repository URL alone — the same repo URL can exist as separate Project rows (different namespaces or registration paths).

**SDK helpers:** `client.Project.is_app(project)`, `is_cli(project)`, and `is_sbom(project)` accept a `Project` model or masked dict row. Map to CSV **`source`** (registration): `is_app` → `Cloud Scan`, else `CLI` (skip SBOM rows with `is_sbom`).

**Latest scan execution:** The bundled script also looks up the newest `ScanResult` per project (`ScanResult.list_by_project`, `mask=spec.environment.config.RunBySystem`) and maps `RunBySystem` to **`latest scan execution`** (`CLI` / `Cloud Scan` / `unknown`). **`mixed mode`** is `true` when registration and latest scan execution disagree — common when app-registered repos still run `endorctl scan` in CI.

**Per-scan execution (API):** Filter `spec.environment.config.RunBySystem` on `ScanResult` ([KB: CLI vs app-based scans](https://kb.endorlabs.com/articles/1109372975-faq-how-to-isolate-cli-based-scans-vs-app-based-scans-executed-in-endor-s-cloud)).

## CSV schema (required)

Write CSV with **exactly these eight columns**, in this order, on every run:

| Column | Source |
|--------|--------|
| **`project name`** | `Project.meta.name` |
| **`namespace`** | `Project.tenant_meta.namespace` |
| **`uuid`** | `Project.uuid` |
| **`source`** | Registration: `CLI` or `Cloud Scan` only |
| **`latest scan execution`** | Newest `ScanResult.spec.environment.config.RunBySystem` → `CLI`, `Cloud Scan`, or `unknown` |
| **`mixed mode`** | `true` when `source` ≠ `latest scan execution` (both known) |
| **`external_installation_id`** | `Project.spec.git.external_installation_id` (empty for CLI) |
| **`installation name`** | Resolved from `Installation` via `spec.external_id`; empty for CLI |

Header row (literal):

```text
project name,namespace,uuid,source,latest scan execution,mixed mode,external_installation_id,installation name
```

Exclude **SBOM projects** (`spec.sbom` set) from the scan and CSV.

## Workflow

### Step 1: Run the bundled script

Default output: `.endorlabs-context/workspace/sessions/<user>/exports/cli-vs-cloud/<tenant>-cli-vs-cloud.csv`

```bash
uv run python .endorlabs-context/sdk/skills/endor-cli-vs-cloud-projects/scripts/classify_cli_vs_cloud_projects.py \
  --tenant <tenant> \
  --output .endorlabs-context/workspace/sessions/<user>/exports/cli-vs-cloud/<tenant>-cli-vs-cloud.csv
```

Optional flags:

- `--project-uuid <uuid>` — classify one or more projects (repeatable).
- `--max-pages <n>` — bound list pagination when requested.
- `--max-workers <n>` — parallel workers for latest `ScanResult` lookup (default 12).
- `--skip-scan-enrichment` — registration-only (`source` column) without scan execution.
- `--summary-json <path>` — optional machine-readable summary alongside chat output.

After `endorlabs.init()`, the script path is also available under `agent-knowledge/skills/endor-cli-vs-cloud-projects/scripts/` in this repository.

### Step 2: Summarize in chat (required)

Always report to the user:

- Tenant, total projects classified, SBOM excluded count.
- **Registration** (`source`): **`Cloud Scan` vs `CLI` counts**.
- **Latest scan execution** counts (`CLI`, `Cloud Scan`, `unknown`).
- **Mixed mode** count and examples when registration ≠ latest scan.
- **Cloud installations** table: `installation name`, `external_installation_id`, project count.
- **CLI-registered** and **CLI-latest-scan** project lists when any exist.
- Path to the CSV written.

Use the script stdout as the source of truth; do not re-list the API for summary numbers.

### Step 3: Apply expectations

| Mode | Expect |
|------|--------|
| **Cloud** | Scheduled/agentless scans; PR scans when configured; scan logs via platform integration; `invalid_installation=True` → rescans blocked until reinstall |
| **CLI** | Scans tied to `endorctl scan` or CI ingest; no SCM app installation id; automation flags on `processing_status` reflect manual/CI workflow |

## Output checklist

Before finishing, confirm:

- [ ] CSV exists with header `project name,namespace,uuid,source,latest scan execution,mixed mode,external_installation_id,installation name`
- [ ] Every data row has **`source`** ∈ {`CLI`, `Cloud Scan`}
- [ ] **`latest scan execution`** populated unless `--skip-scan-enrichment`
- [ ] Cloud rows include resolved **`installation name`** when a matching `Installation` exists
- [ ] SBOM projects excluded
- [ ] Chat summary covers counts, installations, and any CLI exceptions
- [ ] Artifacts under `.endorlabs-context/workspace/sessions/<user>/` (gitignored)

## When to use this skill vs others

| Question | Start here | Then |
|----------|------------|------|
| Is this repo Cloud-integrated or CLI-scanned? | **This skill** | — |
| Cross-namespace duplicate project rows | [endor-duplicate-projects](../endor-duplicate-projects/SKILL.md) | This skill for `source` column |
| Latest findings / scan results for a project | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) | This skill if automation vs manual scan explains empty or stale results |
| Cloud scan failed, metrics spiked, logs between runs | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) | This skill first if unsure whether Cloud automation applies |
| SSO / namespace access for Cloud connector | [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md) | — |

## Related skills

| Need | Skill |
| ---- | ----- |
| Tenant-wide duplicate project inventory | [endor-duplicate-projects](../endor-duplicate-projects/SKILL.md) |
| Findings and ScanResults for one project | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| Scan pipeline RCA (pairs, logs, aggregate diffs) | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Customer Cloud connector / SSO validation | [endor-sso-integration-validation-troubleshooting](../endor-sso-integration-validation-troubleshooting/SKILL.md) |
