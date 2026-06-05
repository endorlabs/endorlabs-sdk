# OpenGrep / Semgrep Rule Syntax Reference

A compact reference card for writing OpenGrep and Semgrep YAML rules,
extended with Endor Labs platform metadata fields.

> **Note:** Both `opengrep` and `semgrep` CLIs accept the same rule YAML
> format. Commands below use `opengrep`; substitute `semgrep` as needed.

For narrative guidance, see [AUTHORING.md](AUTHORING.md).

---

## Rule File Structure

```yaml
rules:
  - id: <string>                     # REQUIRED  Unique kebab-case ID
    languages: [<lang>, ...]         # REQUIRED  e.g. [python], [javascript, typescript]
    severity: <WARNING|ERROR|INFO>   # REQUIRED  Finding severity
    message: |                       # REQUIRED  Multi-line explanation
      Problem: ...
      Solution: ...
    <pattern-key>: ...               # REQUIRED  One of the pattern keys below
    metadata: { ... }                # Optional  Descriptive metadata
    paths:                           # Optional  File scope
      include: [...]
      exclude: [...]
    fix: <string>                    # Optional  Auto-fix replacement
    fix-regex: { ... }               # Optional  Regex-based auto-fix
    options: { ... }                 # Optional  Engine options
```

A file MUST have the top-level `rules:` list wrapper.

---

## Pattern Keys (exactly one required at rule level)

| Key | Type | Behavior |
|-----|------|----------|
| `pattern` | string | Match a single code pattern |
| `patterns` | list | Conjunction (AND) of sub-patterns |
| `pattern-either` | list | Disjunction (OR) of sub-patterns |
| `pattern-regex` | string | Match a regex against source text |

### `pattern` -- Single Pattern

```yaml
pattern: logging.config.listen(...)
```

Matches any call to `logging.config.listen` with any arguments.

### `patterns` -- Conjunction (AND)

```yaml
patterns:
  - pattern: $LOGGER = logging.getLogger(...)
  - pattern-not-inside: |
      $LOGGER = logging.getLogger(...)
      ...
      $LOGGER.addFilter(RedactingFilter(...))
```

All clauses must be satisfied. Positive patterns generate matches;
negative patterns and filters remove them.

### `pattern-either` -- Disjunction (OR)

```yaml
pattern-either:
  - pattern: eval($X)
  - pattern: exec($X)
```

Any clause matching produces a finding.

### `pattern-regex` -- Regex

```yaml
pattern-regex: "api[_-]?key\\s*=\\s*['\"][A-Za-z0-9]{20,}"
```

Matches raw source text. Use sparingly -- AST patterns are more robust.

---

## Sub-Pattern Operators (inside `patterns` or `pattern-either`)

### Positive (generate matches)

| Operator | Scope | Description |
|----------|-------|-------------|
| `pattern` | Expression/statement | Match code that looks like this |
| `pattern-inside` | Block | Match only if surrounded by this context |
| `pattern-regex` | Raw text | Match a regex in source |

### Negative (filter out matches)

| Operator | Scope | Description |
|----------|-------|-------------|
| `pattern-not` | Expression/statement | Exclude matches that look like this pattern |
| `pattern-not-inside` | Block | Exclude matches that appear inside this context |
| `pattern-not-regex` | Raw text | Exclude matches where source matches regex |

### Key distinction: `-not` vs `-not-inside`

- **`pattern-not`**: The matched code itself must NOT have this shape.
  Use for single-line exclusions.
- **`pattern-not-inside`**: The matched code must NOT be surrounded by
  this larger block. Use for multi-line safe-context exclusions
  (e.g., a logger followed by an addFilter call).

---

## Metavariables

| Syntax | Matches | Example |
|--------|---------|---------|
| `$VAR` | Exactly one expression or identifier | `$LOGGER = logging.getLogger(...)` |
| `$_` | Any single expression (anonymous, not unified) | `foo($_, $Y)` |
| `$...VAR` | Zero or more arguments (spread) | `func($...ARGS)` |
| `...` | Zero or more statements/expressions in the same scope | See ellipsis rules below |

### Metavariable unification

Same-name metavariables within a `patterns` block must bind to the same
value. This is how you link a positive and negative pattern to the same
entity.

```yaml
patterns:
  - pattern: $X = open($PATH)
  - pattern-not-inside: |
      $X = open($PATH)
      ...
      $X.close()
```

`$X` is unified -- both clauses refer to the same variable.

---

## Ellipsis (`...`) Rules

1. Matches **zero or more** statements or expressions
2. Stays **within the same block scope** (module level, function body, class body)
3. Does **NOT** cross block boundaries (cannot jump from inside a function to module level)
4. In argument lists, matches zero or more arguments: `func(...)`, `func($X, ...)`
5. In sequences, matches intervening statements:

```yaml
pattern: |
    $LOGGER = logging.getLogger(...)
    ...
    $LOGGER.addFilter(...)
```

This matches even if there are 50 lines of other code between the two
statements, as long as they are in the same scope.

---

## Metavariable Filters

Use inside a `patterns` block after the positive pattern.

### `metavariable-regex`

```yaml
patterns:
  - pattern: $FUNC(...)
  - metavariable-regex:
      metavariable: $FUNC
      regex: "^(eval|exec|compile)$"
```

### `metavariable-pattern`

```yaml
patterns:
  - pattern: $X.query($SQL)
  - metavariable-pattern:
      metavariable: $SQL
      pattern: |
        f"..."
```

The metavariable's value must itself match the given pattern.

### `metavariable-comparison`

```yaml
patterns:
  - pattern: set_timeout($T)
  - metavariable-comparison:
      metavariable: $T
      comparison: $T > 300
```

### `focus-metavariable`

Narrows the reported match location to a specific metavariable:

```yaml
patterns:
  - pattern: $LOGGER = logging.getLogger(...)
  - focus-metavariable: $LOGGER
```

The finding location will point to `$LOGGER` only, not the entire line.

---

## Taint Mode (Skeleton)

For data-flow tracking across functions:

```yaml
rules:
  - id: taint-example
    mode: taint
    languages: [python]
    severity: ERROR
    message: Tainted data reaches sink
    pattern-sources:
      - pattern: request.args.get(...)
    pattern-sinks:
      - pattern: cursor.execute($QUERY, ...)
    pattern-sanitizers:
      - pattern: sanitize($X)
```

Taint mode tracks data from sources to sinks, through sanitizers.
Use for injection vulnerabilities (SQL, XSS, command injection).

---

## Paths (File Scoping)

```yaml
paths:
  include:
    - src/endorlabs/         # Directory prefix
    - "**/*_client.py"       # Glob pattern
  exclude:
    - tests/
    - "*_test.py"
    - "conftest.py"
```

Both `include` and `exclude` accept directory prefixes and glob patterns.
`exclude` takes precedence over `include`.

---

## Auto-Fix

### Literal fix

```yaml
fix: "safe_eval($X)"
```

Replaces the matched code. Metavariables from the pattern are
interpolated.

### Regex fix

```yaml
fix-regex:
  regex: "http://"
  replacement: "https://"
  count: 1       # Optional: only replace first occurrence
```

---

## Options

```yaml
options:
  symbolic_propagation: true    # Track values through assignments
  ac_matching: true             # Associative-commutative matching for operators
  fuzz_generic_unicode: true    # Handle Unicode identifiers
  generic_ellipsis_max_r: 10   # Limit ellipsis expansion depth
```

---

## Severity Mapping

| OpenGrep/Semgrep severity | Endor Labs mapping | Use when |
|---------------------------|-------------------|----------|
| `ERROR` | CRITICAL / HIGH | Exploitable vulnerability, immediate risk |
| `WARNING` | MEDIUM / HIGH | Likely vulnerability, requires context |
| `INFO` | LOW / MEDIUM | Best practice violation, code smell |

The `security-severity` metadata field provides finer control in the
Endor Labs platform:

```yaml
metadata:
  security-severity: High    # Critical, High, Medium, Low
```

---

## Endor Labs Metadata Extensions

These fields in `metadata` are recognized by the Endor Labs platform on
import. They are optional for local scanning but required for full
platform integration.

```yaml
metadata:
  # Standard fields
  category: security
  cwe: ["CWE-532: Insertion of Sensitive Information into Log File"]
  confidence: HIGH
  owasp: ["A09:2021-Security-Logging-and-Monitoring-Failures"]
  references:
    - https://cwe.mitre.org/data/definitions/532.html
  security-severity: High

  # Endor-specific fields
  endor-category: vulnerability         # vulnerability | warning | info
  endor-tags:                           # Searchable tags in the platform
    - OWASP-Top-10
    - Logging
    - SDK-Credential-Leak
  endor-targets:                        # What the rule applies to
    - ENDOR_TARGET_REPOSITORY
  endor-rule-origin:                    # Provenance
    url: https://github.com/org/repo
    license: Apache-2.0
  description: >-                       # Short form (max 1024 bytes for API)
    Logger created without RedactingFilter; secrets may leak.
  explanation: >-                       # Long form (no length limit)
    Full explanation of the vulnerability and its context...
  remediation: >-                       # How to fix
    Attach RedactingFilter to all module-level loggers...
  version: v1.0.0                       # Rule version
```

---

## Test Annotations

Use inline comments to mark expected and non-expected findings in test
files:

```python
# ruleid: my-rule-id
insecure_call()          # This line SHOULD be flagged

# ok: my-rule-id
safe_call()              # This line should NOT be flagged

# todoruleid: my-rule-id
future_detection()       # Known false negative (to be fixed)
```

Run with `semgrep --test` to validate annotations.

---

## Debugging Commands

```bash
# Run a single rule against a directory
opengrep scan --config rule.yaml target/

# JSON output for programmatic analysis
opengrep scan --config rule.yaml target/ --json

# Verbose output (show parsed patterns)
opengrep scan --config rule.yaml target/ --verbose

# Run all rules in a directory
opengrep scan --config rules/ target/

# Dry run (parse rules without scanning)
opengrep scan --config rule.yaml --validate
```

---

## Do / Don't Table

| DO | DON'T |
|----|-------|
| Use `pattern-not-inside` for multi-line safe-context exclusions | Use `pattern-not` for multi-line exclusions (it only matches single expressions) |
| Use `\|` (literal block scalar) for multi-line patterns in YAML | Use `>-` (folded scalar) for patterns -- it collapses newlines |
| Unify metavariable names across positive and negative patterns | Use different `$VAR` names and expect them to refer to the same binding |
| Scope rules with `paths.include` to relevant directories | Leave scope open and filter findings manually |
| Validate locally with `opengrep scan` or `semgrep scan` before importing | Import untested rules to the platform |
| Use `...` within a single scope level | Expect `...` to jump between function bodies or across class boundaries |
| Keep `message` structured (Problem/Solution sections) | Write a one-line message with no remediation guidance |
| Set `metadata.description` to under 1024 bytes for Endor import | Use the full `message` as `description` (may exceed API limit) |
| Wrap rule files in `rules: [...]` at the top level | Omit the wrapper (OpenGrep will reject the file) |
| Use AST patterns (`pattern:`) for structural matching | Rely on `pattern-regex` for things AST patterns handle better |

---

## References

- [AUTHORING.md](AUTHORING.md) -- authoring guide
- [IMPORT_EXPORT.md](IMPORT_EXPORT.md) -- import/export workflow
- [Semgrep Rule Syntax (official)](https://semgrep.dev/docs/writing-rules/rule-syntax)
- [Trail of Bits Quick Reference](https://github.com/trailofbits/skills/blob/main/plugins/semgrep-rule-creator/skills/semgrep-rule-creator/references/quick-reference.md)
