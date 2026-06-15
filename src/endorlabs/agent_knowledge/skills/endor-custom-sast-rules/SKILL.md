---
name: endor-custom-sast-rules
description: Author, validate, and import custom OpenGrep/Semgrep rule YAML into Endor
  Labs SemgrepRule resources. Use when writing or fixing rule syntax, Endor metadata
  shape, local opengrep/semgrep checks, or importing rules to a namespace — not for
  finding triage (hand off to endor-retrieve-scan-results).
---

# Custom SemgrepRule authoring and import

Write OpenGrep/Semgrep-compatible YAML, validate shape, import as platform
**`SemgrepRule`** rows.

## Scope

**In scope:** rule YAML syntax and formatting; Endor `/semgrep-rules` shape and
metadata guardrails; local `opengrep`/`semgrep` checks; SDK +
`sast_rule_manager.py` validate/import/delete/sync; **`SemgrepRule`** metadata
inventory (`endor-semgrep-inventory`).

**Out of scope:** repository-wide threat modeling; individual **Finding** triage —
[endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md).

## 1. Author rule YAML

1. Start from a reference rule — `.endorlabs-context/semgrep-rules/`, [semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules), or an existing tenant **`SemgrepRule`**.
2. Required top-level keys: `id`, `languages`, `severity`, `message`. Add Endor metadata (`endor-category`, `endor-tags`, `endor-targets`) when importing to the platform.
3. Use `|` (literal block) for multi-line patterns — not `>-` (folded).
4. Scope with `paths.include` / `paths.exclude` when needed.

| Doc | Use for |
| --- | --- |
| [authoring.md](authoring.md) | Pattern strategies, pitfalls, Endor metadata |
| [syntax-reference.md](syntax-reference.md) | Operator syntax card |
| [semgrep-rule-shape-guardrails.md](semgrep-rule-shape-guardrails.md) | API-accepted keys, metadata inventory |

## 2. Validate (before import)

**Layer 1 — local engine (recommended):**

```bash
opengrep scan --config path/to/rule.yaml --validate
# or: semgrep scan --config path/to/rule.yaml --validate
```

Optional scan against a target tree: `opengrep scan --config rule.yaml target/`.

**Layer 2 — platform shape (SDK, no API write):**

```bash
uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
  validate --rules-dir opengrep-rules/ --namespace "$ENDOR_NAMESPACE"
```

Runs skill guardrails (`normalize_rule_dict_for_semgrep_crud`) plus
`endorlabs.resources.semgrep_rule.validate_semgrep_rule()` (payload checks).

**Layer 3 — server:** there is **no** separate SemgrepRule validate RPC in the
public OpenAPI spec — the platform validates on **`SemgrepRule.create`** /
**update** (expect `400` on bad payloads). Use import `--dry-run` only for a
local pass; it does not call the server.

## 3. Import to platform

Use `sast_rule_manager.py` for **`SemgrepRule`** CRUD (authoring path below; same
relative path under `src/endorlabs/agent_knowledge/skills/` in the wheel):

```bash
uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
  import --rules-dir opengrep-rules/ --namespace tenant.ns --dry-run

uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
  sync --rules-dir opengrep-rules/ --enabled-dir opengrep-rules/enabled/ \
  --name-filter "my-prefix" --namespace tenant.ns --force
```

| Command | Purpose |
| --- | --- |
| `validate` | Guardrails + SDK payload validation (no API) |
| `import` | Create/update **`SemgrepRule`** rows |
| `delete` / `orphans` | Remove rules and stale findings |
| `configure` | Enable/disable by directory |
| `sync` | delete → orphans → import → configure |

Platform types, export, and troubleshooting: [import-export.md](import-export.md).

## 4. Optional: verify with scan

```bash
endorctl scan --sast
```

Compare counts with local opengrep/semgrep on the same target.

## SemgrepRule metadata inventory

```bash
uv run endor-semgrep-inventory --namespace tenant.namespace
```

Lists tenant **`SemgrepRule`** rows and summarizes metadata-key prevalence —
see [semgrep-rule-shape-guardrails.md](semgrep-rule-shape-guardrails.md).

## Naming (CLI vs API resource)

Workflow **`semgrep-inventory`** / CLI **`endor-semgrep-inventory`** operate on
**`SemgrepRule`** via `client.SemgrepRule.list()` — not a separate “Semgrep” API kind.

## Related skills

| Need | Skill |
| ---- | ----- |
| Findings after scan | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
