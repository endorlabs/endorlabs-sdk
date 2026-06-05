---
name: agent-skill-authoring
description: >-
  Author or update an Endor Labs agent skill under agent-knowledge/skills/: portable
  Cursor/Claude frontmatter, optional endorlabs.catalog workflow linkage, and
  contract frontmatter. Use when adding skills, fixing sync validation errors,
  or migrating workflow catalog metadata.
---

# Author or update an agent skill

Read [`schema/README.md`](README.md) first — it is the canonical authoring spec.

## Checklist

1. Create `agent-knowledge/skills/<name>/` where `<name>` matches `^[a-z0-9-]{1,64}$`.
2. Add `SKILL.md` with portable `name`, `description` (third person, WHAT + WHEN).
3. If the skill maps to a workflow CLI, add `endorlabs.catalog` (authoring only).
4. Add reference `.md` / scripts only when `SKILL.md` would become too long.
5. Run `uv run python devtools/sync_agent_knowledge.py` and fix validation errors.
6. Confirm shipped bundle `SKILL.md` has **no** `endorlabs:` key.

## Workflow linkage

- Skill-linked workflows: `endorlabs.catalog` in `SKILL.md`.
- Rows without a skill (`context-bootstrap`, `endor-demo`): [`workflows.yaml`](../workflows.yaml).

## Rules and contracts

- Bootstrap harness rules: `agent-knowledge/rules/<id>.md` per [`rule.schema.json`](rule.schema.json) (`id`, `tags`, `summary`).
- Reference contracts: `agent-knowledge/contracts/<id>.md` per [`contract.schema.json`](contract.schema.json) (`id`, `tags`).

## Validation

Sync validates against JSON schemas in this directory and cross-checks `catalog.cli` against `pyproject.toml` `[project.scripts]`.
