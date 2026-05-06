# Semgrep Rule Shape Guardrails

This document defines the parser-safe YAML shape for Endor Labs
`/semgrep-rules` CRUD operations and how the skill manager handles keys.

## Canonical top-level rule shape

Required keys:

- `id`
- `languages`
- `message`
- `severity` (`ERROR`, `WARNING`, `INFO`)

At least one pattern key is required:

- `pattern`
- `patterns`
- `pattern-either`
- `pattern-regex`
- `pattern-sources`
- `pattern-sinks`

## Metadata handling policy

The manager uses a skill-local key map and normalization logic in
`.cursor/skills/custom-sast-rules/scripts/sast_rule_manager.py`.

- **Accepted**: keys listed in `ALLOWED_METADATA_KEYS`
- **Dropped with warning**: unknown keys
- **Dropped with warning**: parser-unsupported keys for CRUD path:
  - `short-description`
  - `shortDescription`
- **Rejected**: `metadata.description` above 1024 UTF-8 bytes

## Why this exists

The `/semgrep-rules` parser rejects some keys that may appear in other
ingestion paths. Guardrails prevent platform-side failures by normalizing
rule metadata before create/update.

## Tenant metadata inventory

Use the inventory script to snapshot metadata key usage in your tenant:

```bash
uv run endor-semgrep-inventory --namespace tenant.namespace
```

Outputs:

- `artifacts/semgrep_rule_metadata_inventory.json`
- `artifacts/semgrep_rule_metadata_inventory.md`

The JSON contains per-key prevalence and representative rule examples
(`meta.name`, `defined_by`, `uuid`) to help decide which fields should be
preserved in source YAML.
