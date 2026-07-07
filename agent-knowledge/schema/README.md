# Agent authoring schema

Authoritative guide for writing agent knowledge under [`agent-knowledge/`](../). Skills must round-trip to [Cursor Agent Skills](https://docs.cursor.com) and [Anthropic Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

`agent-knowledge/schema/` is **maintainer-only** — sync does not ship it in the wheel.

## Directory layout

```
agent-knowledge/
  INDEX.md          # Tier-0 agent index (shipped)
  README.md         # Skill index (authoring)
  workflows.yaml    # Supplemental workflow rows (skill: null)
  schema/           # This directory (not shipped)
  rules/*.md        # Harness bootstrap (sync → .cursor/rules/*.mdc; footgun subset always-on)
  contracts/*.md    # Reference SDK semantics (on demand)
  skills/<name>/    # Task playbooks
    SKILL.md
    *.md, scripts/
```

Run `uv run python devtools/sync_agent_knowledge.py` after edits. CI `--verify` enforces drift (`tests/unit/platform/context/test_agent_knowledge_drift.py`).

**Schema files:** [`skill.schema.json`](skill.schema.json), [`rule.schema.json`](rule.schema.json), [`contract.schema.json`](contract.schema.json), [`workflows.schema.json`](workflows.schema.json), [`changelog-intake.schema.json`](changelog-intake.schema.json) (optional PR intake fields; reference only).

Unit tests for the shipped bundle should assert **structure** (unique ids, on-disk paths, bootstrap consistency)—not exact skill or workflow counts. Counts change whenever skills are added, removed, or demoted to workflow-only rows.

### Path consistency (tests and docs)

Skill directory names (`endor-*`), script paths, and runtime examples in `SKILL.md` must stay aligned across:

| Tree | Role |
|------|------|
| `agent-knowledge/skills/<id>/` | Authoring source |
| `src/endorlabs/agent_knowledge/skills/<id>/` | Shipped wheel (sync output) |
| `.cursor/skills/<id>/` | Cursor mirror (optional; `init(sync_skills=…)`) |

When you rename a skill or move a script:

1. Grep `tests/` for the old skill id or filename; update inline path loaders (e.g. `tests/unit/tooling/scripts/test_sast_rule_manager.py`, `test_sso_access_spotcheck.py`).
2. Update command examples in skill docs and related guides under `docs/`.
3. Run sync and fix `--verify` drift before push.

Do not introduce shared test utilities for path resolution — agents and contributors update the citing tests and docs directly.

## Portable frontmatter (shipped in bundle `SKILL.md`)

Only these keys appear in the generated bundle:

| Field | Required | Rules |
|-------|----------|-------|
| `name` | yes | `^endor-[a-z0-9-]{1,59}$`; must match directory name |
| `description` | yes | 1–1024 chars; third person; **WHAT** + **WHEN** |
| `disable-model-invocation` | no | Cursor-only; omit unless `true` |

Authoring validation uses the full [`skill.schema.json`](skill.schema.json); sync writes only the portable subset above into the wheel bundle.

Every skill `name` and directory **must** use the `endor-*` prefix (same family as `endor-context`, `endor-callgraph-search`, …). Sync and schema reject unprefixed ids.

**Scope and handoffs in `description`:** When a skill covers only part of a larger RCA or workflow, say so in `description` (WHAT + WHEN + **what is out of scope**). Example: *“… Not for individual Finding rows or policy validation — hand off to other skills when deeper analysis is needed.”* See [Skill composition and handoffs](#skill-composition-and-handoffs) below.

## Skill composition and handoffs

Skills are playbooks, not silos. When a task commonly spans multiple concerns (scan pipeline vs finding rows vs policy vs lineage), **document how skills flow into each other** so agents stop at the right boundary and escalate with a link—not by improvising API calls outside the skill’s scope.

**Canonical example:** the scan-regression cluster — [`troubleshooting-scans`](../skills/endor-troubleshooting-scans/SKILL.md) (pipeline, heuristic pairs, logs, aggregate diffs) → [`retrieve-scan-results`](../skills/endor-retrieve-scan-results/SKILL.md) (Finding rows by scan UUID) → [`validate-policy`](../skills/endor-validate-policy/SKILL.md), [`reachability-provenance`](../skills/endor-reachability-provenance/SKILL.md), [`dependency-finding-provenance`](../skills/endor-dependency-finding-provenance/SKILL.md), or [`dependency-provenance`](../skills/endor-dependency-provenance/SKILL.md) as needed.

### When to add composition docs

Add handoff guidance when **any** of these apply:

- The skill uses **heuristics** or aggregate metrics instead of platform truth (say so explicitly).
- The skill is **compositional** (CLI artifact chain or optional steps).
- Common user questions **continue** in a sibling skill (findings, policies, lineage, reachability).
- The skill’s **scope is intentionally narrow** (e.g. only `ScanResult` stats, not `Finding.list`).

Simple one-shot skills may only need a short **Related skills** table; full RCA playbooks should use the sections below.

### Recommended sections (precedent)

Use these headings in `SKILL.md` body (order may vary; omit sections that do not apply):

| Section | Purpose |
| -------- | -------- |
| **Scope** | **In scope** vs **Out of scope** bullet lists. Out-of-scope items link to the owning skill: `[endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)`. |
| **When to use this skill vs others** | Optional routing table: symptom/goal → start skill → then skill. |
| **Optional stops** | For artifact chains: which module/flag to stop after and when (e.g. `--regression-only`). |
| **Related skills** | Compact table at end (or after main workflow): Need → Skill link. Keep rows to skills that are **direct** handoffs, not the whole catalog. |
| **Outputs** | Default path under `workspace/runs/<run-bucket>/` or `workspace/projects/`; run bucket = catalog `workflow_id` or skill id minus `endor-`; override flag (`--output` / `--output-dir`). |
| **Naming (optional footer)** | When a **CLI name, workflow id, or module path** uses domain shorthand but the API resource differs, state both once near the workflow step — e.g. `endor-semgrep-inventory` lists **`SemgrepRule`** via `client.SemgrepRule.list()`, not a separate “Semgrep” resource kind. Do not rename shipped CLIs; be explicit in prose. |

**Intro blurb:** One or two sentences after the title can point **to** or **from** a sibling skill when users often start on the wrong playbook (e.g. retrieve-scan-results → troubleshooting-scans for pipeline failure).

### Link format

- Use **relative** paths between skills: `../<skill-dir>/SKILL.md` (matches directory `name`).
- Link to **skills**, not repo paths like `agent-skills/` or `.cursor/skills/`.
- When you add outbound handoffs from skill A to B, **update B’s Related skills** (reciprocal pointer) in the same PR unless B truly has nothing to send back.

### Supplementary doc filenames

Each skill directory has **`SKILL.md`** (required). Additional reference files use **lowercase kebab-case** (e.g. `call-graph-format-and-search.md`, `policy-validation-api.md`). Avoid ambiguous single-word names like `api.md`. Fixed entrypoint names elsewhere in the repo (`README.md`, `INDEX.md`, `AGENTS.md`) follow their existing conventions.

### Heuristic and aggregate skills

If output is scored, ranked, or summarized (not authoritative platform state):

- State **heuristic** in the module section and in interpretation hints.
- Name the signals (e.g. adjacent-pair score from `ScanResult.spec.stats` aggregates).
- Clarify what a boolean like `regression_detected` **means in code** (e.g. score > 0), not colloquial “regression.”
- Say when to **stop** and hand off for row-level data (e.g. use scan UUIDs from pairs artifact with `Finding.list_for_context(scan)` per [retrieve-scan-results](../skills/endor-retrieve-scan-results/SKILL.md); do not filter on `context.scan_uuid` — see [resource-discovery](../contracts/resource-discovery.md)).

### What not to do

- Do not duplicate another skill’s full workflow—link and list the entry condition.
- Do not imply platform-defined “anomaly” or “regression” when the implementation is client-side scoring.
- Do not add Related skills rows for every skill in `INDEX.md`; only **direct** next/previous steps in typical RCA.


## Authoring-only frontmatter (`endorlabs.catalog`)

Authoring `SKILL.md` may include an `endorlabs.catalog` block (validated by the full skill schema). Sync **strips** the entire `endorlabs` key from shipped bundle `SKILL.md`.

| Field | Required | Purpose |
|-------|----------|---------|
| `workflow_id` | yes | Catalog row id (`^[a-z0-9-]+$`); often matches skill id minus `endor-` |
| `module` | yes | Import path for the workflow implementation |
| `cli` | no | Console script name when the workflow is exposed as a CLI |
| `default_output` | no | Default artifact directory under `workspace/runs/<run-bucket>/` |
| `agent_visible` | no | Include in agent-facing workflow catalog (default `true`) |
| `composition` | no | `artifact_chain`, `library_api`, or `cli_only` |
| `library_entrypoints` | no | Callable symbols when `composition` is `library_api` |

Example shape (authoring only):

```yaml
endorlabs:
  catalog:
    workflow_id: troubleshooting-scans
    module: endorlabs.workflows.troubleshooting_scans
    composition: artifact_chain
    agent_visible: true
```

See live examples under `agent-knowledge/skills/*/SKILL.md`.

## Rules (`agent-knowledge/rules/`)

Harness bootstrap invariants. Each `rules/<id>.md` file starts with:

```yaml
---
id: endor-namespace-scoping
tags: [list, namespace, traverse]
summary: >-
  Resolve Project first; pass namespace=project.namespace on project-scoped lists.
---
```

Validated by [`rule.schema.json`](rule.schema.json). Every rule `id` **must** use the `endor-*` prefix (same namespace as skills and workflow CLIs). Shipped rules are listed in `MANIFEST.json` → `rules[]` and `bootstrap.rule_ids`; generates `.cursor/rules/<id>.mdc` with tooling-only provenance (`x-endor-generated`, `x-endor-source`, `x-endor-source-sha256`). Stale generated rules are pruned via the `x-endor-generated` marker.

**Maintainer-only rules** (`MAINTAINER_ONLY_RULE_IDS` in `devtools/agent_knowledge_catalog.py`, e.g. `endor-changelog`): remain under `agent-knowledge/rules/` and sync to `.cursor/rules/`, but are **not** copied into the wheel bundle.

**Cursor apply mode** (see `CURSOR_ALWAYS_APPLY_RULE_IDS` / `CURSOR_BOOTSTRAP_RULE_GLOBS` in `devtools/sync_agent_knowledge.py`):

- **Always-on footguns:** `endor-namespace-scoping`, `endor-list-query-performance`
- **Glob-scoped (maintainer / automation paths):** the other bootstrap rules — `src/endorlabs/**`, `**/*.py`, `.endorlabs-context/**`, `agent-knowledge/**`, `docs/**`, `devtools/**`

Hand-maintained Cursor rules (no `x-endor-generated`): `agent-knowledge-authoring`, `docs-skillbase-consistency` only.

## Contracts (`agent-knowledge/contracts/`)

On-demand reference semantics. Each `contracts/<id>.md` file starts with:

```yaml
---
id: list-parameters
tags: [list, mask, filter]
---
```

Validated by [`contract.schema.json`](contract.schema.json). Shipped under `agent_knowledge/contracts/`; listed in `MANIFEST.json` → `contracts[]`.

## Path rewrites at sync

| Authoring | Shipped / materialized |
|-----------|------------------------|
| `agent-knowledge/skills/` | `sdk/skills/` |
| `agent-knowledge/rules/` | `sdk/rules/` |
| `agent-knowledge/contracts/` | `sdk/contracts/` |

## Machine schemas

| File | Purpose |
|------|---------|
| [`skill.schema.json`](skill.schema.json) | `SKILL.md` frontmatter |
| [`rule.schema.json`](rule.schema.json) | Rule frontmatter |
| [`contract.schema.json`](contract.schema.json) | Contract frontmatter |
| [`workflows.schema.json`](workflows.schema.json) | `workflows.yaml` |
| [`changelog-intake.schema.json`](changelog-intake.schema.json) | PR description intake block (reference; not CI-gated) |

## Meta-skill

Shipped playbook: [`endor-author-agent-skill`](../skills/endor-author-agent-skill/SKILL.md). [`SKILL.md`](SKILL.md) in this directory is a short pointer for maintainers editing `schema/` directly.
