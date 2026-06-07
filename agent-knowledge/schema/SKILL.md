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

1. Create `agent-knowledge/skills/<name>/` where `<name>` matches `^endor-[a-z0-9-]{1,59}$` (every skill id is **`endor-*`**).
2. Add `SKILL.md` with portable `name`, `description` (third person, WHAT + WHEN; note out-of-scope handoffs when the skill is narrow).
3. If the skill maps to a workflow CLI, add `endorlabs.catalog` (authoring only).
4. Add reference `.md` / scripts only when `SKILL.md` would become too long.
5. If the skill is compositional, heuristic, or part of a multi-skill RCA path, add **Scope**, optional **Optional stops** / routing table, and **Related skills** per [schema/README.md — Skill composition and handoffs](README.md#skill-composition-and-handoffs). Update reciprocal links on peer skills in the same change.
6. Run `uv run python devtools/sync_agent_knowledge.py` and fix validation errors.
7. Confirm shipped bundle `SKILL.md` has **no** `endorlabs:` key.
8. **Path consistency:** grep `tests/` and `docs/` for the skill id and any script paths; update inline test loaders and doc examples in the same PR (see [schema/README.md — Path consistency](README.md#path-consistency-tests-and-docs)).

## Workflow linkage

- Skill-linked workflows: `endorlabs.catalog` in `SKILL.md`.
- Rows without a skill (e.g. `context-bootstrap`): [`workflows.yaml`](../workflows.yaml).

## Rules and contracts

- Bootstrap harness rules: `agent-knowledge/rules/<id>.md` per [`rule.schema.json`](rule.schema.json) (`id`, `tags`, `summary`).
- Reference contracts: `agent-knowledge/contracts/<id>.md` per [`contract.schema.json`](contract.schema.json) (`id`, `tags`).

## Validation

Sync validates against JSON schemas in this directory and cross-checks `catalog.cli` against `pyproject.toml` `[project.scripts]`.
