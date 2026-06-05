# Agent skill authoring schema

Authoritative guide for writing skills in [`agent-skills/`](../). Skills must round-trip to [Cursor Agent Skills](https://docs.cursor.com) and [Anthropic Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

`agent-skills/schema/` is **maintainer-only** — sync does not ship it in the wheel.

## Directory layout

```
agent-skills/
  schema/           # This directory (not shipped)
  README.md         # Skill index
  INDEX.md          # Tier-0 agent index (shipped)
  workflows.yaml    # Supplemental workflow rows (skill: null)
  contracts/*.md    # Tier-0 contracts with YAML frontmatter
  <skill-name>/     # Folder name MUST equal frontmatter name
    SKILL.md        # Portable frontmatter + body
    *.md, scripts/  # Optional reference files
```

Run `uv run python devtools/sync_agent_bundle.py` after edits. CI `--verify` enforces drift.

## Portable frontmatter (shipped in bundle `SKILL.md`)

Only these keys appear in the generated bundle:

| Field | Required | Rules |
|-------|----------|-------|
| `name` | yes | `^[a-z0-9-]{1,64}$`; must match directory name |
| `description` | yes | 1–1024 chars; third person; **WHAT** + **WHEN** |
| `disable-model-invocation` | no | Cursor-only; omit unless `true` |

Validated by [`skill.schema.json`](skill.schema.json) (portable subset).

### Description best practices

- Write in **third person** (the skill does X, not "I will…").
- Lead with **what** the skill accomplishes, then **when** to use it.
- Keep under 1024 characters; agents inject this into discovery context.

## Endor extension block (authoring only)

Optional `endorlabs.catalog` links a skill to a workflow CLI/module row. Sync **strips** the entire `endorlabs` key from shipped `SKILL.md`.

```yaml
---
name: project-agent-context
description: >-
  Deterministic project context bundle...
endorlabs:
  catalog:
    workflow_id: agent-context
    cli: endor-agent-context
    module: endorlabs.workflows.agent_context.cli
    default_output: .endorlabs-context/workspace/projects/<uuid>/
    agent_visible: true
---
```

| `endorlabs.catalog` field | Required | Notes |
|---------------------------|----------|-------|
| `workflow_id` | yes | Stable catalog id |
| `module` | yes | Python entry module |
| `cli` | when script exists | Must match `pyproject.toml` `[project.scripts]` |
| `default_output` | for agent-visible workflows | Context-relative path or `stdout` phrasing |
| `agent_visible` | default `true` | `false` for maintainer-only |

Skills **without** `endorlabs.catalog` are playbook-only (indexed in `MANIFEST.skills` only).

Supplemental workflow rows with no skill live in [`workflows.yaml`](../workflows.yaml).

## Contracts

Each `contracts/<id>.md` file starts with:

```yaml
---
id: canonical-naming
tags: [naming, facades]
---
```

Validated by [`contract.schema.json`](contract.schema.json). Body is copied verbatim to the bundle.

## Progressive disclosure

1. **Metadata** — `name` + `description` (always in agent discovery).
2. **SKILL.md body** — loaded when the task matches.
3. **Reference files** — loaded only when needed.

## Path rewrites at sync

Authoring paths `agent-skills/` become runtime `sdk/skills/` in shipped bodies and refs.

## Machine schemas

| File | Purpose |
|------|---------|
| [`skill.schema.json`](skill.schema.json) | `SKILL.md` frontmatter |
| [`contract.schema.json`](contract.schema.json) | Contract frontmatter |
| [`workflows.schema.json`](workflows.schema.json) | `workflows.yaml` |

## Meta-skill

[`SKILL.md`](SKILL.md) in this directory is an optional agent playbook for authoring or updating skills.
