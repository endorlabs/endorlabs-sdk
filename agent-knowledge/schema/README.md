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
  rules/*.md        # Harness bootstrap (always load; generates .cursor/rules/*.mdc)
  contracts/*.md    # Reference SDK semantics (on demand)
  skills/<name>/    # Task playbooks
    SKILL.md
    *.md, scripts/
```

Run `uv run python devtools/sync_agent_knowledge.py` after edits. CI `--verify` enforces drift.

## Portable frontmatter (shipped in bundle `SKILL.md`)

Only these keys appear in the generated bundle:

| Field | Required | Rules |
|-------|----------|-------|
| `name` | yes | `^[a-z0-9-]{1,64}$`; must match directory name |
| `description` | yes | 1–1024 chars; third person; **WHAT** + **WHEN** |
| `disable-model-invocation` | no | Cursor-only; omit unless `true` |

Validated by [`skill.schema.json`](skill.schema.json) (portable subset).

## Endor extension block (authoring only)

Optional `endorlabs.catalog` links a skill to a workflow CLI/module row. Sync **strips** the entire `endorlabs` key from shipped `SKILL.md`. See prior examples in skill `SKILL.md` files under `agent-knowledge/skills/`.

## Rules (`agent-knowledge/rules/`)

Harness bootstrap invariants. Each `rules/<id>.md` file starts with:

```yaml
---
id: namespace-scoping
tags: [list, namespace, traverse]
summary: >-
  Resolve Project first; pass namespace=project.namespace on project-scoped lists.
---
```

Validated by [`rule.schema.json`](rule.schema.json). Listed in `MANIFEST.json` → `rules[]` and `bootstrap.rule_ids`; generate always-on `.cursor/rules/<id>.mdc` with tooling-only provenance (`x-endor-generated`, `x-endor-source`, `x-endor-source-sha256`).

Hand-maintained Cursor rules: `agent-knowledge-authoring`, `docs-skillbase-consistency` only.

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

## Meta-skill

[`SKILL.md`](SKILL.md) in this directory is an optional agent playbook for authoring or updating skills.
