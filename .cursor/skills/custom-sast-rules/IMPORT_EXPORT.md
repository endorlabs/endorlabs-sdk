# Importing and Exporting Semgrep Rules with Endor Labs

How to push custom OpenGrep/Semgrep rules into an Endor Labs namespace
using the import maneuver, and how to export existing rules for local
editing or backup.

---

## Prerequisites

### Environment variables

Set these in your `.env` file or shell environment:

| Variable | Purpose |
|----------|---------|
| `ENDOR_API_CREDENTIALS_KEY` | API key for Endor Labs authentication |
| `ENDOR_API_CREDENTIALS_SECRET` | API secret for Endor Labs authentication |
| `ENDOR_NAMESPACE` | Target namespace (e.g., `tenant.child`) |

The maneuver scripts read these automatically. On Windows PowerShell,
load `.env` manually if your shell does not source it:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$') {
        Set-Item -Path "env:$($Matches[1])" -Value $Matches[2]
    }
}
```

On Linux/macOS with `direnv`:

```bash
# .envrc
dotenv
```

### Dependencies

```bash
uv sync            # Installs the SDK and all dependencies
pip install pyyaml # If not already available (included in SDK extras)
```

### Validated rule YAML

Before importing, always validate the rule locally:

```bash
opengrep scan --config path/to/rule.yaml target/directory/
# or: semgrep scan --config path/to/rule.yaml target/directory/
```

See [AUTHORING.md](AUTHORING.md) for the full validation loop.

---

## Import Workflow

```
Author YAML --> Validate with opengrep/semgrep --> Import with maneuver --> Verify with endorctl
```

### Step 1: Author and validate

Write the rule YAML following [AUTHORING.md](AUTHORING.md). Run it
through OpenGrep or Semgrep locally and confirm findings match your
expectations.

### Step 2: Import

```bash
# Import a single rule file
uv run python maneuvers/import_semgrep_rule.py \
    --file .endorlabs-context/semgrep-rules/my-rule.yaml \
    --namespace tenant.namespace

# Import all rules in a directory
uv run python maneuvers/import_semgrep_rule.py \
    --dir .endorlabs-context/semgrep-rules/ \
    --namespace tenant.namespace

# Dry run (parse and validate without calling the API)
uv run python maneuvers/import_semgrep_rule.py \
    --file my-rule.yaml --dry-run

# Force update (overwrite existing rule with same name)
uv run python maneuvers/import_semgrep_rule.py \
    --file my-rule.yaml --force

# Verbose logging
uv run python maneuvers/import_semgrep_rule.py \
    --file my-rule.yaml --verbose
```

### Step 3: Verify

Run a SAST scan against the repository to confirm the imported rule
produces findings:

```bash
endorctl scan --sast
```

Compare the finding count and affected files against your local
OpenGrep/Semgrep results.

---

## Import Maneuver CLI Reference

| Flag | Description |
|------|-------------|
| `--file PATH` | Import a single YAML rule file |
| `--dir PATH` | Import all `.yaml`/`.yml` files in a directory |
| `--namespace NS` | Target namespace (overrides `ENDOR_NAMESPACE`) |
| `--dry-run` | Parse and validate without calling the API |
| `--force` | Update existing rules (matched by `meta.name`) |
| `--verbose` | Enable DEBUG-level logging |

Either `--file` or `--dir` is required (not both).

---

## Export Maneuver CLI Reference

```bash
# Export a rule by UUID
uv run python maneuvers/export_semgrep_rule.py \
    --uuid <rule-uuid> --namespace tenant.namespace

# Export a rule by name
uv run python maneuvers/export_semgrep_rule.py \
    --name my-rule-id --namespace tenant.namespace

# Export all custom rules
uv run python maneuvers/export_semgrep_rule.py \
    --all --namespace tenant.namespace

# List rules matching a filter (dry run)
uv run python maneuvers/export_semgrep_rule.py \
    --filter "meta.name contains my-rule" --dry-run
```

| Flag | Description |
|------|-------------|
| `--uuid UUID` | Export a specific rule by UUID |
| `--name NAME` | Export a specific rule by `meta.name` |
| `--filter EXPR` | List rules matching an Endor filter expression |
| `--all` | Export all custom rules in the namespace |
| `--namespace NS` | Target namespace (overrides `ENDOR_NAMESPACE`) |
| `--dry-run` | List matching rules without downloading YAML |
| `--output-dir DIR` | Directory to write exported YAML files |

---

## SDK Types Involved

The import maneuver uses these types from `endorlabs.resources.semgrep_rule`:

| Type | Purpose |
|------|---------|
| `SemgrepRule` | Full rule object returned by the API |
| `SemgrepRuleSpec` | Contains `rule` (structured) and `yaml` (raw YAML string) |
| `SemgrepNativeRule` | Structured representation of the rule for client-side validation |
| `CreateSemgrepRulePayload` | Request body for creating a rule |
| `UpdateSemgrepRulePayload` | Request body for updating a rule |
| `SemgrepRuleMetaCreate` | Metadata for the `meta` field (`name`, `description`) |

### How `spec.yaml` and `spec.rule` relate

The API stores the rule in two forms:

- **`spec.yaml`**: The raw YAML string (wrapped in `rules: [...]`).
  This is the authoritative definition. The API parses it server-side.
- **`spec.rule`**: A structured `SemgrepNativeRule` object with fields
  like `id`, `languages`, `message`, `severity`, `pattern`, `mode`.
  Used for client-side validation and display.

The `spec.rule` Pydantic model does NOT fully represent all Semgrep
pattern operators (e.g., `pattern-not-inside`, `patterns` as a list).
The full rule lives in `spec.yaml`.

---

## API Constraints (Learned the Hard Way)

### `meta.description` max 1024 bytes

The API rejects payloads where `meta.description` exceeds 1024 bytes
(UTF-8 encoded).

**Workaround:** Use the short `metadata.description` from the rule YAML
(not the full `message`). If it still exceeds 1024 bytes, truncate:

```python
if len(description.encode("utf-8")) > 1024:
    description = description[:1020] + "..."
```

### `spec.yaml` must be wrapped in `rules:` envelope

The API expects the YAML string to have the top-level `rules:` list,
even for a single rule. If the parsed YAML is a bare rule dict, wrap
it:

```python
import yaml

if isinstance(parsed, dict):
    wrapped = yaml.dump({"rules": [parsed]}, default_flow_style=False)
elif isinstance(parsed, dict) and "rules" in parsed:
    wrapped = yaml.dump(parsed, default_flow_style=False)
```

### Client-side validation may reject valid rules

The SDK's Pydantic model for `SemgrepNativeRule` does not represent
all Semgrep pattern operators. A rule using `patterns` with
`pattern-not-inside` will fail client-side validation even though the
API accepts it fine.

**Workaround:** Pass `validate=False` to `create_semgrep_rule()`:

```python
created = create_semgrep_rule(client, namespace, payload, validate=False)
```

The rule YAML is already validated by your local OpenGrep/Semgrep run;
the API parses `spec.yaml` server-side regardless.

### `spec.rule` is still required

Even when using `validate=False`, the `spec.rule` field must be
populated with a minimal `SemgrepNativeRule` object. Extract only the
fields the model recognizes:

```python
from endorlabs.resources.semgrep_rule import SemgrepNativeRule

native_rule = SemgrepNativeRule(
    id=rule_dict.get("id"),
    languages=rule_dict.get("languages"),
    message=rule_dict.get("message"),
    severity=rule_dict.get("severity"),
    pattern=rule_dict.get("pattern"),    # May be None for complex rules
    mode=rule_dict.get("mode"),
)
```

For rules using `patterns` (compound rules), `pattern` will be `None`.
This is acceptable -- the API uses `spec.yaml` as the source of truth.

---

## Idempotency and Updates

The import maneuver checks for existing rules by matching `meta.name`.

| Scenario | Behavior |
|----------|----------|
| Rule does not exist | Creates a new rule |
| Rule exists, no `--force` | Skips with a warning |
| Rule exists, `--force` | Updates the existing rule (preserving UUID) |

The `meta.name` is derived from the rule's `id` field in the YAML.

---

## Verification Checklist

After importing, verify end-to-end:

1. **Platform UI**: Navigate to the Endor Labs console and confirm the
   rule appears in the custom rules list under your namespace.

2. **SAST scan**: Run `endorctl scan --sast` against the target
   repository.

3. **Finding comparison**: Compare findings:
   - Local OpenGrep/Semgrep finding count should match platform finding count
   - File paths in findings should align
   - Severity levels should match

4. **Example verification** (from the RedactingFilter rule):
   ```
   Local OpenGrep:  27 files, 27 findings
   Platform scan:   27 files, 28 findings (one file had two loggers)
   Verdict:         ALIGNED
   ```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "Namespace is required" | `ENDOR_NAMESPACE` not set | Load `.env` or pass `--namespace` |
| "spec.rule is required" | `CreateSemgrepRulePayload.spec.rule` is `None` | Build a minimal `SemgrepNativeRule` (see above) |
| "Meta.Description: value length must be at most 1024 bytes" | `meta.description` too long | Truncate to 1020 chars + "..." |
| "Semgrep rule validation failed" | Client-side Pydantic validation rejects pattern operators | Pass `validate=False` to `create_semgrep_rule()` |
| Rule imported but no findings in scan | Rule `paths.include` does not match scanned files, or rule is disabled | Check rule YAML scope; verify rule is enabled in the namespace |
| "already exists" / duplicate | Rule with same `meta.name` exists | Use `--force` to update, or choose a different name |

---

## References

- [AUTHORING.md](AUTHORING.md) -- authoring guide
- [SYNTAX_REFERENCE.md](SYNTAX_REFERENCE.md) -- rule syntax card
- [THREAT_MODEL.md](THREAT_MODEL.md) -- threat modeling checklist
