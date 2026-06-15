# Importing and Exporting SemgrepRule resources

How to push custom OpenGrep/Semgrep rule YAML into Endor Labs as **`SemgrepRule`**
rows, export existing rules, and validate before create.

## Validation (no dedicated validate endpoint)

The public OpenAPI spec exposes **`SemgrepRule` CRUD only** (`GET`/`POST`
`/semgrep-rules`, `GET`/`DELETE` by UUID) — **not** a separate validate RPC.
The platform rejects invalid payloads on **create/update** (`400`).

**Before import, prefer:**

1. Local engine: `opengrep scan --config rule.yaml --validate`
2. Skill manager: `sast_rule_manager.py validate --rules-dir … --namespace …`
   — runs guardrails + `validate_semgrep_rule()` from
   `endorlabs.resources.semgrep_rule` (SDK-only, no API write)
3. Import dry-run: `import --dry-run` (guardrails only; still no server round-trip)

---

## Prerequisites

### Environment variables

Set these in your `.env` file or shell environment:

| Variable | Purpose |
|----------|---------|
| `ENDOR_API_CREDENTIALS_KEY` | API key for Endor Labs authentication |
| `ENDOR_API_CREDENTIALS_SECRET` | API secret for Endor Labs authentication |
| `ENDOR_NAMESPACE` | Target namespace (e.g., `tenant.child`) |

`sast_rule_manager.py` and other SDK workflow scripts read these from the environment. Load a local `.env` with **`uv run --env-file .env`** (see [README.md](../../../README.md#configuration)):

```bash
uv run --env-file .env endorctl api list --resource Project -n tenant.ns
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

See [authoring.md](authoring.md) for the full validation loop.

---

## Import Workflow

```
Author YAML --> Validate with opengrep/semgrep --> Import with sast_rule_manager --> Verify with endorctl
```

### Step 1: Author and validate

Write the rule YAML following [authoring.md](authoring.md). Run it
through OpenGrep or Semgrep locally and confirm findings match your
expectations.

### Step 2: Import

```bash
# Import all rules in a directory (validates each rule first)
uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
    import --rules-dir opengrep-rules/ --namespace tenant.ns

# Force update existing rules
uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
    import --rules-dir opengrep-rules/ --namespace tenant.ns --force

# Dry run (parse, validate, and log planned actions without calling the API)
uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
    import --rules-dir opengrep-rules/ --namespace tenant.ns --dry-run

# Verbose logging
uv run python sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \
    import --rules-dir opengrep-rules/ --namespace tenant.ns --verbose
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

## SAST Rule Manager CLI Reference

The script is at `sdk/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py`.

### Common flags (all subcommands)

| Flag | Description |
|------|-------------|
| `--namespace NS` | Target namespace (required, no default) |
| `--dry-run` | Log planned actions without calling the API |
| `--verbose` | Enable DEBUG-level logging |

### `import` -- Import rules from a directory

```bash
sast_rule_manager.py import --rules-dir PATH [--force] [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--rules-dir PATH` | Directory containing rule YAML files (recursive) |
| `--force` | Update existing rules (matched by `meta.name`) |

Each rule dict is normalized through the Semgrep CRUD guardrails before
import. Unknown metadata keys are warned-and-dropped; required shape
violations still fail fast.

### `delete` -- Delete rules by name filter

```bash
sast_rule_manager.py delete --name-filter SUBSTRING [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--name-filter SUBSTRING` | Substring match on `meta.name` via `matches` regex (not `contains`) |

Returns the list of deleted rule names, which can be passed to
`orphans` for cleanup.

### `orphans` -- Clean orphaned findings

```bash
sast_rule_manager.py orphans --deleted-names NAME [NAME ...] [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--deleted-names NAME [...]` | Rule names whose findings should be cleaned up |

Fetches all SAST findings and client-side matches on
`meta.description` / `spec.extra_key` (API filters are unreliable for
this).

### `configure` -- Enable/disable rules by directory

```bash
sast_rule_manager.py configure --rules-dir PATH --enabled-dir PATH [--dry-run]
```

| Flag | Description |
|------|-------------|
| `--rules-dir PATH` | Directory containing all rule YAML files |
| `--enabled-dir PATH` | Directory whose rules should be enabled; all others disabled |

### `sync` -- Full lifecycle

```bash
sast_rule_manager.py sync --rules-dir PATH --enabled-dir PATH \
    [--name-filter SUBSTRING] [--force] [--dry-run]
```

Chains: `delete` -> `orphans` -> `import` -> `configure`. If
`--name-filter` is omitted, the delete step is skipped.

| Flag | Description |
|------|-------------|
| `--rules-dir PATH` | Directory containing all rule YAML files |
| `--enabled-dir PATH` | Directory whose rules should be enabled |
| `--name-filter SUBSTRING` | Substring for delete step via `meta.name matches` (optional) |
| `--force` | Update existing rules during import step |

---

## Exporting Rules

To export rules from the platform, use the SDK to list and retrieve them:

```python
import endorlabs

client = endorlabs.Client(tenant="tenant.namespace")

# List all custom rules
rules = client.SemgrepRule.list()

# Get a specific rule by UUID
rule = client.SemgrepRule.get(uuid="<rule-uuid>")

# Access the rule spec for YAML content
print(rule.spec)
```

For bulk export, iterate over the list results and write each rule's spec to a YAML file.

---

## Validation Guardrail: CRUD shape normalization

The SAST Rule Manager normalizes every rule dict before import. This is
the gate an agent must pass for `/semgrep-rules` create/update safety.

### Allowed metadata keys

Only these keys are accepted under `metadata:` in rule YAML. The list
matches `v1SemgrepRuleMeta` from the Endor Labs API spec.

| Key | Example value |
|-----|---------------|
| `asvs` | ASVS reference |
| `author` | Rule author name |
| `bandit-code` | `B608` |
| `category` | `security` |
| `confidence` | `HIGH` |
| `cwe` | `CWE-532` |
| `cwe2020-top25` | `true` |
| `cwe2021-top25` | `true` |
| `cwe2022-top25` | `true` |
| `cwe2023-top25` | `true` |
| `deprecated` | `true` |
| `description` | Short rule description (max 1024 UTF-8 bytes) |
| `display-name` | Human-readable rule name |
| `endor-attack-examples` | `[https://example.com/attack]` |
| `endor-category` | `code-quality` |
| `endor-rule-origin` | `endorlabs` |
| `endor-tags` | `[credential-protection, trust-chain.id:my-chain]` |
| `endor-targets` | `[src/endorlabs/]` |
| `explanation` | Extended explanation for findings |
| `functional-categories` | `[crypto::search]` |
| `help` | Help text for rule |
| `impact` | Impact description |
| `interfile` | `true` |
| `license` | `MIT` |
| `likelihood` | `HIGH` |
| `masvs` | `[MASVS-CRYPTO-1]` |
| `owasp` | `A02:2021` |
| `owaspapi` | `API1:2023` |
| `precision` | `VERY_HIGH` |
| `references` | List of reference URLs |
| `remediation` | How to fix the finding |
| `resources` | List of resource references |
| `rule-origin-note` | Origin note |
| `security-severity` | `7.5` |
| `severity` | `ERROR` |
| `short-description` | Brief description (also accepted as `shortDescription`) |
| `shortDescription` | Brief description (camelCase variant) |
| `source-rule-url` | URL to source rule |
| `source-url-open` | Open source URL |
| `subcategory` | `[vuln, audit]` |
| `tags` | `[cwe-89, owasp-top10]` |
| `technology` | `[python, flask]` |
| `version` | `1` |
| `vulnerability` | Vulnerability identifier |
| `vulnerability-class` | `[SQL-Injection]` |

Any other key under `metadata` is dropped with a structured warning so
imports can proceed without backend parser failures.

### Accepted vs dropped vs rejected

- Accepted: known metadata keys from `v1SemgrepRuleMeta`
- Dropped with warning: unknown metadata keys
- Dropped with warning: parser-unsupported keys (`short-description`, `shortDescription`)
- Rejected with error: missing `id`/`languages`/`message`/`severity`
- Rejected with error: missing all pattern keys
- Rejected with error: invalid `severity` value
- Rejected with error: `metadata.description` over 1024 UTF-8 bytes

### Checks performed

1. Required top-level keys: `id`, `languages`, `severity`, `message`
2. At least one pattern key: `pattern`, `patterns`, `pattern-either`, `pattern-regex`, `pattern-sources`
3. `severity` must be one of `WARNING`, `ERROR`, `INFO`
4. Unknown `metadata` keys are dropped with warning
5. `metadata.description` must not exceed 1024 UTF-8 bytes

---

## SDK Types Involved

The SAST Rule Manager uses these types from `endorlabs.resources.semgrep_rule`:

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

The `spec.rule` Pydantic model (`SemgrepNativeRule`) now covers
the most common Semgrep pattern operators (including
`pattern-not-inside`, `pattern-inside`, compound `patterns`, etc.)
and uses `extra="allow"` for forward compatibility. The authoritative
rule definition still lives in `spec.yaml`.

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

The `import` subcommand checks for existing rules by matching `meta.name`.

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
| "Meta.Description: value length must be at most 1024 bytes" | `meta.description` too long | Truncate to 1020 chars + "..." (handled automatically by the script) |
| "Semgrep rule validation failed" | Client-side Pydantic validation rejects pattern operators | The script uses `validate=False` by default |
| "Dropped unknown metadata key(s)" warning | Rule YAML contains fields not in CRUD allowlist | Keep import result, then migrate dropped fields into supported keys |
| "Dropped parser-unsupported metadata key(s)" warning | Rule contains parser-breaking keys for `/semgrep-rules` | Remove those keys from source YAML (`short-description`, `shortDescription`) |
| Rule imported but no findings in scan | Rule `paths.include` does not match scanned files, or rule is disabled | Check rule YAML scope; use `configure` to enable |
| "already exists" / duplicate | Rule with same `meta.name` exists | Use `--force` to update, or choose a different name |
| Orphaned findings after rule deletion | Findings persist after their rule is deleted | Run `orphans` or `sync` (includes orphan cleanup automatically) |
| "Unable to parse rule specification: unknown field" | API rejects metadata key not in its schema | Check `ALLOWED_METADATA_KEYS`; move custom data into `endor-tags` |

---

## References

- [authoring.md](authoring.md) -- authoring guide
- [syntax-reference.md](syntax-reference.md) -- rule syntax card
