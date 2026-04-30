---
name: custom-sast-rules
description: >-
  Author, validate, and import custom OpenGrep/Semgrep SAST rules into the
  Endor Labs platform. Use when the user wants to write security rules,
  perform threat modeling for SAST, create absence-detection rules, validate
  rule YAML, or import Semgrep rules into Endor Labs.
---

# Custom SAST Rules Workflow

End-to-end: threat model a repository, author rule YAML, validate locally, import to Endor Labs, verify.

## Phase 1: Threat Model

Identify what custom rules the codebase needs before writing any YAML.

1. **Threat canvas** -- answer: what credential types, trust boundaries, consumers, log frameworks, existing safety measures?
2. **Credential lifecycle** -- trace each secret through four stages:

   ```
   ENTER --> TRANSIT --> REST --> EXIT
   ```

   Focus SAST rules on TRANSIT and EXIT (accidental exposure).

3. **CWE checklist** -- for SDKs/libraries, prioritize: CWE-798 (hardcoded creds), CWE-532 (log leaks), CWE-209 (error exposure), CWE-311 (missing encryption), CWE-319 (cleartext transmission), CWE-94 (code injection).

4. **Presence vs absence** -- most rules detect the *presence* of something dangerous. The highest-impact SDK rules detect the *absence* of something safe (e.g., logger without redaction filter). Absence rules use `pattern` + `pattern-not-inside`.

5. **Capture as spec** before writing YAML:

   ```
   Threat:       [description]
   CWE:          [CWE-NNN]
   Detection:    [presence / absence]
   Safe pattern: [compliant code]
   Unsafe pattern: [non-compliant code]
   Scope:        [directories]
   Confidence:   [HIGH / MEDIUM / LOW]
   ```

For the full checklist and worked example, see [THREAT_MODEL.md](THREAT_MODEL.md).

## Phase 2: Author Rule YAML

1. **Start from a reference rule** -- never from scratch. Sources: `.endorlabs-context/semgrep-rules/`, [semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules), Endor Labs platform UI.

2. **Choose pattern strategy**:
   - **Presence** (simple): `pattern: dangerous_call(...)`
   - **Absence** (compound): `patterns:` with positive `pattern` + `pattern-not-inside` for the safe context
   - **Either/or**: `pattern-either:` list

3. **Metavariable unification** -- use the same `$VAR` name in positive and negative patterns so they bind to the same value.

4. **Scope** with `paths.include` / `paths.exclude` to reduce noise.

5. **Required fields**: `id`, `languages`, `severity`, `message`. Add Endor metadata: `endor-category`, `endor-tags`, `endor-targets`.

6. **YAML scalar**: use `|` (literal block) for multi-line patterns, never `>-` (folded).

For pattern strategies, pitfalls, and worked examples, see [AUTHORING.md](AUTHORING.md).
For the full syntax card, see [SYNTAX_REFERENCE.md](SYNTAX_REFERENCE.md).

## Phase 3: Validate Locally

Both `opengrep` and `semgrep` CLIs accept the same rule YAML format:

```bash
# Run rule against target directory
opengrep scan --config path/to/rule.yaml target/
# or: semgrep scan --config path/to/rule.yaml target/

# JSON output for programmatic checks
opengrep scan --config path/to/rule.yaml target/ --json

# Parse-only validation (no scan)
opengrep scan --config path/to/rule.yaml --validate
```

Verify: compiles without errors, flags expected files, zero false positives.

## Phase 4: Import to Platform

Use the SAST Rule Manager script (`scripts/sast_rule_manager.py`) for all platform operations. It validates every rule against the API-accepted schema before import and handles orphaned findings on delete.

```bash
# Import all rules (validates each rule dict before calling the API)
uv run python .cursor/skills/custom-sast-rules/scripts/sast_rule_manager.py \
    import --rules-dir opengrep-rules/ --namespace tenant.ns --force

# Full sync (delete old + orphan cleanup + import + configure enable/disable)
uv run python .cursor/skills/custom-sast-rules/scripts/sast_rule_manager.py \
    sync --rules-dir opengrep-rules/ --enabled-dir opengrep-rules/trust-chain/ \
    --name-filter "endor-sdk" --namespace tenant.ns --force

# Validate only (dry run -- parses, validates, logs planned actions)
uv run python .cursor/skills/custom-sast-rules/scripts/sast_rule_manager.py \
    import --rules-dir opengrep-rules/ --namespace tenant.ns --dry-run

# Delete rules matching a name filter and clean up orphaned findings
uv run python .cursor/skills/custom-sast-rules/scripts/sast_rule_manager.py \
    delete --name-filter "endor-sdk" --namespace tenant.ns

# Configure enable/disable states by directory
uv run python .cursor/skills/custom-sast-rules/scripts/sast_rule_manager.py \
    configure --rules-dir opengrep-rules/ \
    --enabled-dir opengrep-rules/trust-chain/ --namespace tenant.ns
```

### Subcommands

| Command | Purpose |
|---------|---------|
| `import` | Import rules from a directory; validates each rule first |
| `delete` | Delete rules by name filter; returns names for orphan cleanup |
| `orphans` | Clean stale findings referencing deleted rules |
| `configure` | Enable rules from one dir, disable all others |
| `sync` | Full lifecycle: delete -> orphans -> import -> configure |

For SDK types, API constraints, validation guardrails, and export workflow, see [IMPORT_EXPORT.md](IMPORT_EXPORT.md).

## Phase 5: Verify

```bash
endorctl scan --sast
```

Compare finding count and affected files against local OpenGrep/Semgrep results. They should align (platform may report +1 if a file has multiple match sites).

## Quick Reference

| Phase | Tool | Output |
|-------|------|--------|
| Threat model | Manual / checklist | Threat spec per finding |
| Author | Text editor + reference rules | Rule YAML file |
| Validate | `opengrep scan` / `semgrep scan` | Finding count + file list |
| Import | `scripts/sast_rule_manager.py` | Rule created in namespace |
| Verify | `endorctl scan --sast` | Platform findings match local |
