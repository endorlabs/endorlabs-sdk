# Authoring OpenGrep / Semgrep Rules

How to go from a threat-model finding to a validated OpenGrep rule YAML
file, ready for local scanning and import into the Endor Labs platform.

This guide assumes you have completed the threat-modeling step described in
[threat-modeling-for-sast-rules.md](threat-modeling-for-sast-rules.md).

---

## 1. Start from a Reference Rule

Never write a rule from scratch.  Find an existing rule that is
structurally close to what you need and adapt it.

Good sources for reference rules:
- `.endorlabs-context/semgrep-rules/` (rules already imported into your namespace)
- [semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules) (community registry)
- The Endor Labs platform UI (export a rule with the export maneuver)

### Anatomy of a rule file

```yaml
rules:
  - id: rule-identifier              # Unique kebab-case ID
    languages: [python]              # Target language(s)
    severity: WARNING                # WARNING | ERROR | INFO
    message: |                       # Multi-line: what/why/how-to-fix
      Problem: ...
      Solution: ...
    metadata:                        # Descriptive fields (not pattern logic)
      category: security
      cwe: ["CWE-532: ..."]
      confidence: HIGH
      # Endor-specific metadata (see syntax reference)
      endor-category: vulnerability
      endor-tags: [...]
      endor-targets: [ENDOR_TARGET_REPOSITORY]
    patterns:                        # The detection logic
      - pattern: ...
      - pattern-not-inside: |
          ...
    paths:                           # Scope limiter
      include: [src/]
```

Key takeaway: `patterns` is the detection logic; everything else is
metadata and scoping.

---

## 2. Choose the Right Pattern Strategy

### Presence detection (simple)

Use when the vulnerability IS the dangerous call itself.

```yaml
# Detects: logging.config.listen(...)
pattern: logging.config.listen(...)
```

One `pattern` key at the rule level.  Matches any occurrence.

### Absence detection (compound)

Use when the vulnerability is a MISSING safety measure.

```yaml
# Detects: logger without RedactingFilter
patterns:
  - pattern: $LOGGER = logging.getLogger(...)
  - pattern-not-inside: |
      $LOGGER = logging.getLogger(...)
      ...
      $LOGGER.addFilter(RedactingFilter(...))
```

This requires a `patterns` list (conjunction) with:
1. A positive `pattern` that matches the entity to check
2. A `pattern-not-inside` that describes the safe context

If the entity matches the positive pattern but is NOT inside the safe
context, the rule fires.

### Either/or detection

Use when multiple patterns indicate the same vulnerability.

```yaml
pattern-either:
  - pattern: eval($X)
  - pattern: exec($X)
```

---

## 3. How `patterns` Evaluation Works

The `patterns` key is a conjunction (AND).  Evaluation order:

1. **Positive patterns run first** -- `pattern`, `pattern-inside`,
   `pattern-regex`.  These generate the initial set of matches.
2. **Negative patterns filter** -- `pattern-not`, `pattern-not-inside`,
   `pattern-not-regex`.  These remove matches from the set.
3. **Conditionals refine** -- `metavariable-regex`,
   `metavariable-pattern`, `metavariable-comparison`,
   `focus-metavariable`.

A match must satisfy ALL clauses.  If any negative pattern matches, the
finding is suppressed.

---

## 4. Critical Concepts

### Ellipsis (`...`) scope rules

The `...` operator matches zero or more statements/expressions
**within the same block scope**.

```python
# This WILL match (same module-level scope):
logger = logging.getLogger(__name__)
x = 42
logger.addFilter(RedactingFilter([...]))
```

**Limitation:** `...` does NOT cross block boundaries (e.g., it cannot
jump from inside a function into the module level, or from one class
method into another).

### Metavariable unification

When you use the same metavariable name (`$LOGGER`) in multiple pattern
clauses within the same `patterns` block, OpenGrep/Semgrep **unifies**
them -- both must bind to the same concrete value.

```yaml
patterns:
  - pattern: $LOGGER = logging.getLogger(...)
  - pattern-not-inside: |
      $LOGGER = logging.getLogger(...)
      ...
      $LOGGER.addFilter(RedactingFilter(...))
```

Here, `$LOGGER` in the positive pattern and `$LOGGER` in the negative
pattern must refer to the same variable.  This prevents the rule from
being fooled by a different logger having a filter.

### `pattern-not-inside` vs `pattern-not`

| Operator | Scope | Use when |
|----------|-------|----------|
| `pattern-not-inside` | Checks that the match is NOT surrounded by a larger code block | Excluding a multi-line safe context (e.g., logger + addFilter) |
| `pattern-not` | Checks that the match itself does NOT look like a given pattern | Excluding specific single-line forms (e.g., a particular function name) |

**Common mistake:** Using `pattern-not` when you need
`pattern-not-inside`.  If the safe pattern is multi-line (setup +
subsequent call), you must use `pattern-not-inside`.

---

## 5. Scoping with `paths`

Limit the rule to relevant directories to reduce noise:

```yaml
paths:
  include:
    - src/endorlabs/
  exclude:
    - tests/
    - "*_test.py"
```

If omitted, the rule scans all files matching the `languages` filter.

---

## 6. Metadata Fields

### Required fields

- `id`: Unique kebab-case identifier
- `languages`: List of target languages
- `severity`: `WARNING`, `ERROR`, or `INFO`
- `message`: Multi-line description with Problem and Solution sections

### Standard metadata

- `category`: `security`, `correctness`, `best-practice`, `performance`
- `cwe`: List of CWE strings (e.g., `"CWE-532: ..."`)
- `confidence`: `HIGH`, `MEDIUM`, `LOW`
- `owasp`: List of OWASP IDs
- `references`: List of URLs

### Endor Labs extensions

These are recognized by the Endor Labs platform when rules are imported:

| Field | Purpose | Example |
|-------|---------|---------|
| `endor-category` | Maps to Endor finding type | `vulnerability` |
| `endor-tags` | Searchable tags in the platform | `[OWASP-Top-10, Logging]` |
| `endor-targets` | What the rule targets | `[ENDOR_TARGET_REPOSITORY]` |
| `endor-rule-origin.url` | Source repository URL | `https://github.com/...` |
| `endor-rule-origin.license` | Rule license | `Apache-2.0` |
| `security-severity` | Severity string for platform display | `High` |

---

## 7. Validation Loop

Always validate locally before importing into the platform.

### Step 1: Run with default output

```bash
opengrep scan --config path/to/rule.yaml target/directory/
```

Check that:
- The rule compiles without errors
- It flags the files you expect
- It does NOT flag files that are already compliant

### Step 2: Run with JSON for programmatic checks

```bash
opengrep scan --config path/to/rule.yaml target/directory/ --json
```

Parse the JSON to verify:
- Total finding count matches your manual audit
- Each finding has the correct `check_id`, file path, and line range
- No false positives

### Step 3: Compare against known state

If you have a known list of compliant and non-compliant files, verify:

```
Expected non-compliant: 27 files
Actual findings:        27 files  (PASS)
Expected compliant:     12 files (with RedactingFilter)
False positives:        0         (PASS)
```

---

## 8. Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Using `pattern-not` instead of `pattern-not-inside` | Rule fires on files that have the safe pattern | Switch to `pattern-not-inside` with full multi-line context |
| YAML `>-` folding in patterns | Pattern string loses newlines, stops matching multi-line code | Use `\|` (literal block) for patterns that span lines |
| Forgetting metavariable unification | Rule is fooled by a different variable having the filter | Use the same `$VAR` name in positive and negative patterns |
| Ellipsis crossing blocks | Rule does not match because `...` cannot exit a function scope | Restructure: match at the scope level where both lines coexist |
| Overly broad scope | Rule fires on test files or generated code | Add `paths.include` / `paths.exclude` |
| Missing `rules:` wrapper | OpenGrep rejects the file | Always wrap with `rules: [...]` at the top level |

---

## 9. Worked Example: RedactingFilter Rule

**Threat:** Module-level loggers in the Endor Cockpit SDK may emit API
keys, bearer tokens, and OAuth callback tokens at DEBUG level if the
`RedactingFilter` is not attached.

**CWE:** CWE-532 (Insertion of Sensitive Information into Log File)

**Strategy:** Absence detection -- flag loggers WITHOUT the filter.

**Positive pattern:**
```yaml
pattern: $LOGGER = logging.getLogger(...)
```
Matches any module-level logger assignment.

**Negative pattern (safe context):**
```yaml
pattern-not-inside: |
    $LOGGER = logging.getLogger(...)
    ...
    $LOGGER.addFilter(RedactingFilter(...))
```
If the logger is followed (anywhere in the same scope) by an
`addFilter(RedactingFilter(...))` call, suppress the finding.

**Scope:** `paths.include: [src/endorlabs/]`

**Result:** 27 non-compliant files flagged, 12 compliant files
correctly suppressed, 0 false positives.

After local validation, the rule was imported into Endor Labs using the
import maneuver (see [importing-semgrep-rules-into-endor.md](importing-semgrep-rules-into-endor.md))
and verified with `endorctl scan --sast` (28 findings across 27 files,
matching the local results exactly).

---

## References

- [OpenGrep Rule Syntax Reference](opengrep-rule-syntax-reference.md)
- [Importing Semgrep Rules into Endor](importing-semgrep-rules-into-endor.md)
- [Threat Modeling for SAST Rules](threat-modeling-for-sast-rules.md)
- [Semgrep Rule Syntax (official docs)](https://semgrep.dev/docs/writing-rules/rule-syntax)
