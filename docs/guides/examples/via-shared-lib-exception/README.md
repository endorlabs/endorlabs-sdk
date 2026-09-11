# Via shared-library exception (portable Rego example)

Except vulnerability findings that enter a **consumer** package only through a
**direct** shared library (parent_version_name walk), without excepting findings
owned by the shared library itself.

## Files

- [`exception.rego`](exception.rego) — drop-in `POLICY_TYPE_EXCEPTION` rule

## Create

1. Set `shared_lib_substr` to a coordinate substring of the shared library
   (example uses `com.example.shared:common-lib`).
2. Create an exception policy with:
   - **Query:** `data.via_shared_lib_exception.match_finding`
   - **Resource kinds:** `Finding`, `DependencyMetadata`, `PackageVersion`
   - **Project scope:** consumer projects only (exclude the shared-lib producer)
   - **`disable=true`** until a live dry-run / rescan looks right
3. Enable and rescan when ready; action policies (e.g. Jira) resolve when
   findings no longer match after the next scan.

## What not to use

| Approach | Why it fails for “via shared lib” |
|----------|-----------------------------------|
| SCA template **Dependency Name** = shared lib | Matches the **leaf** name, not intermediate parents |
| Blanket `FINDING_TAGS_TRANSITIVE` | Too broad (all transitive vulns) |
| `FINDING_TAGS_PATH_EXTERNAL` alone | Polyrepo-only; does not fire in monorepos |

## Validation notes

- **Policy create/update** rejects invalid Rego (arity conflicts, missing
  resource kinds). Prefer that as the compile gate.
- **PolicyValidation** compile-check (`disable_preview`) works for this rule
  when comments avoid embedding a `data.<package>` path (the validator may
  treat that comment text as a data reference).
- PolicyValidation **match** preview does **not** load DependencyMetadata joins
  for this pattern — empty `policy_output` is expected. Prove matches with a
  live DM parent-walk oracle or enable + rescan.

## Lab dry-run shape

Consumer package depends on shared lib only; control package depends on the
vulnerable leaf directly. Forward exception should match consumer (via) and
not match control or the shared-lib producer.
