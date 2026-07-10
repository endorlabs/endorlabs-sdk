---
name: endor-author-agent-skill
description: >-
  Author or update a shipped agent skill under agent-knowledge/skills/: portable
  frontmatter, optional endorlabs.catalog workflow linkage, composition handoffs,
  sync, and drift verification. Use when adding skills, fixing sync validation
  errors, or migrating workflow catalog metadata—not for extending SDK resources
  (endor-implement-sdk-resource) or runtime API troubleshooting.
---

# Author or update an agent skill

Canonical spec: [schema/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/schema/README.md) (frontmatter, `endorlabs.catalog`, composition, rules, contracts, `workflows.yaml`). Machine validation: [skill.schema.json](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/schema/skill.schema.json).

**Write path:** edit `agent-knowledge/skills/<id>/` → run sync → commit authoring **and** `src/endorlabs/agent_knowledge/` bundle output. Do not hand-edit the shipped tree.

## Scope

**In scope**

- New skill directories under `agent-knowledge/skills/` (`endor-*` id)
- `SKILL.md` portable frontmatter and playbook body
- Optional reference `.md` files and scripts in the skill directory
- `endorlabs.catalog` in authoring frontmatter when the skill maps to a workflow CLI
- Reciprocal **Related skills** links on peer skills in the same PR
- `agent-knowledge/README.md` skill table row when adding a skill
- Running `devtools/codegen/sync_agent_knowledge.py` and fixing validation errors

**Out of scope**

- Hand-editing `src/endorlabs/agent_knowledge/` (sync output)
- New workflow Python modules or `[project.scripts]` CLIs without a contributor workflow PR — see [workflows.yaml](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/workflows.yaml) and [endor-workflow-composition](../../rules/endor-workflow-composition.md)
- SDK resource / OpenAPI surface work → [endor-implement-sdk-resource](../endor-implement-sdk-resource/SKILL.md)
- Runtime SDK or API errors → [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md)

## Checklist

### 1. Create the skill directory

```text
agent-knowledge/skills/<id>/
  SKILL.md          # required
  *.md, scripts/    # optional reference files (kebab-case names)
```

- `<id>` must match `^endor-[a-z0-9-]{1,59}$` and equal the `name` in frontmatter.
- Every shipped skill id uses the **`endor-*`** prefix.

### 2. Author `SKILL.md` frontmatter

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Same as directory name (`endor-*`) |
| `description` | yes | Third person; **WHAT** + **WHEN**; note out-of-scope handoffs when narrow |
| `disable-model-invocation` | no | Cursor-only; set `true` only when the skill must not auto-invoke |
| `endorlabs.catalog` | no | Authoring only — sync strips the entire `endorlabs` key from the bundle |

Example workflow linkage (authoring frontmatter only):

```yaml
endorlabs:
  catalog:
    workflow_id: policies-validate
    module: endorlabs.workflows.policies.validate
    agent_visible: true
```

`catalog.cli` must match a `[project.scripts]` entry in `pyproject.toml` when set.

### 3. Write the playbook body

Keep `SKILL.md` actionable. Link to `docs/` and sibling skills instead of duplicating full reference material.

When the skill is compositional, heuristic, or part of a multi-skill RCA path, add:

- **Scope** (in scope / out of scope with skill links)
- **Related skills** (direct handoffs only)
- Optional **When to use this skill vs others** routing table
- Optional **Optional stops** for artifact chains
- **Outputs** — run bucket + default path + override flags (see [workspace-layout](../../rules/endor-workspace-layout.md)) When skill A hands off to B, update B's **Related skills** in the same PR unless B has nothing to send back.

**Portable examples:** use placeholders (`<tenant>`, `<namespace>`, `<project-uuid>`) — never commit estate identifiers. See [endor-portable-examples](../../rules/endor-portable-examples.md).

### 4. Workflow rows without a skill

Supplemental workflow catalog rows with `skill: null` (e.g. `context-bootstrap`) live in [workflows.yaml](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/workflows.yaml), not in a skill directory.

### 5. Sync and verify

```bash
uv run python devtools/codegen/sync_agent_knowledge.py
uv run python devtools/codegen/sync_agent_knowledge.py --verify
```

Sync regenerates:

- `src/endorlabs/agent_knowledge/skills/`
- `MANIFEST.json`, `INDEX.md`, workflow index entries
- `.cursor/rules/*.mdc` from `agent-knowledge/rules/` (generated rules only)

Confirm shipped bundle `SKILL.md` contains **only** portable frontmatter (`name`, `description`, optional `disable-model-invocation`) — no `endorlabs:` key.

Drift gate: `tests/unit/platform/context/test_agent_knowledge_drift.py`.

### 6. Path consistency (same PR)

Grep `tests/` and `docs/` for the skill id and any script paths:

- Update inline test loaders (e.g. `tests/unit/tooling/scripts/test_*.py`) — no shared path-helper modules
- Update cross-links under `agent-knowledge/skills/` and durable docs that cite the skill
- Add a row to [agent-knowledge/README.md](../../INDEX.md) skill table

Do **not** hardcode skill or workflow counts in unit tests.

### 7. Changelog (user-facing skills)

New shipped skills with distinct playbooks → **Added** under `docs/changelog.md` → **Unreleased**. See [endor-changelog](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/rules/endor-changelog.md).

## Rules and contracts (related authoring)

| Kind | Location | Schema |
|------|----------|--------|
| Bootstrap rules | `agent-knowledge/rules/<id>.md` | [rule.schema.json](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/schema/rule.schema.json) |
| Reference contracts | `agent-knowledge/contracts/<id>.md` | [contract.schema.json](https://github.com/endorlabs/endorlabs-sdk/blob/main/agent-knowledge/schema/contract.schema.json) |

Hand-maintained Cursor rules (not synced from `rules/`): `agent-knowledge-authoring`, `docs-skillbase-consistency`.

## Related skills

| Need | Skill |
|------|-------|
| New workflow CLI + library module to link from `endorlabs.catalog` | [endor-implement-sdk-resource](../endor-implement-sdk-resource/SKILL.md) (if API surface) · [endor-workflow-composition](../../rules/endor-workflow-composition.md) |
| Sync / manifest validation failures after skill edit | This skill (sync checklist) · [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) (if runtime SDK errors) |
| OpenAPI / model-sync drift unrelated to skills | [endor-model-sync-drift](../endor-model-sync-drift/SKILL.md) |
