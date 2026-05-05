---
name: reachability-provenance
description: Investigates reachability provenance mismatches in vulnerability findings by comparing dependency reachability, function reachability, and vulnerability metadata in the oss namespace. Use when finding tags or summary text appear contradictory (for example reachable dependency with unreachable function), when validating affected_callpath_uris attribution, or when analyzing CVE/GHSA alias consistency.
disable-model-invocation: true
---

# Reachability Provenance

## Purpose

Use this skill to triage findings where reachability signals conflict, especially:

- `REACHABLE_DEPENDENCY` with `UNREACHABLE_FUNCTION`
- summary text saying no vulnerable function is reachable despite suspicious callgraph evidence
- disagreement between CVE and GHSA vulnerability records

## What "oss namespace" is used for

Use the `oss` namespace as the canonical vulnerability provenance source for:

- vulnerability records returned by query/evaluation
- `affected` entries and version ranges
- `affected_callpath_uris` and `affected_filepaths`
- alias consistency checks across CVE/GHSA IDs
- source attribution fields (for example `SOURCE_OSV`, `SOURCE_ENDOR`)

Do not infer function-level provenance from advisory prose alone when structured `affected_callpath_uris` are available in `oss`.

## Workflow

1. Gather finding evidence
   - Record finding UUID, tags, summary, `target_dependency_package_name`, `extra_key`, and `call_graph_analysis_type`.
   - Record whether `reachable_paths` is present.

2. Gather vulnerability provenance from `oss`
   - Fetch vulnerability objects by aliases (for example CVE and GHSA names) in `oss`.
   - For each relevant affected package entry, extract:
     - package identity + ecosystem
     - `affected_callpath_uris`
     - `affected_filepaths`
     - ranges (introduced/fixed/last_affected)
     - source field (`SOURCE_*`)

3. Compare strict function map vs graph evidence
   - Strict check: vulnerable function reachability should be determined from `affected_callpath_uris`.
   - Practical-risk check: inspect whether risky API surface in the same package is reachable even when strict vulnerable callpaths are not matched.

4. Classify mismatch type
   - **Provenance fragmentation**: aliases disagree or one alias lacks structured function mapping.
   - **Signature normalization mismatch**: semantically equivalent functions fail strict URI matching.
   - **True unreachable function**: dependency reachable, but no strict or equivalent function evidence.
   - **Likely reachable function**: strict or equivalent callpath evidence exists.

5. Produce normalized verdict
   - Distinguish:
     - dependency-level reachability conclusion
     - strict function-level reachability conclusion
     - practical exploitability signal
   - State confidence and likely owner:
     - vuln metadata curation
     - function signature normalization/matching
     - callgraph coverage limitations

## Output Template

Use this structure in the final triage result:

```markdown
## Reachability Provenance Result

- Finding: <finding-id>
- Target dependency: <package@version>
- Call graph analysis type: <full|precomputed|unspecified>

- Dependency reachability: <reachable|unreachable|unknown>
- Function reachability (strict): <reachable|unreachable|unknown>
- Practical risk signal: <present|not present>

- OSS vulnerability provenance:
  - Alias records checked: <list>
  - Structured function map consistency: <consistent|fragmented|missing>
  - Primary source used for function attribution: <SOURCE_*>

- Likely disconnect:
  - <one sentence>

- Recommended next action:
  - <normalization/curation/coverage action>
```

## Guardrails

- Do not hardcode a single CVE-specific heuristic.
- Do not treat advisory text as equivalent to structured callpath mapping.
- Prefer structured `affected_callpath_uris` from `oss` for strict conclusions.
- If strict and practical signals diverge, report both explicitly.
- Keep all examples and analysis tenant-neutral and customer-neutral.

## Additional Resources

- For sample triage outcomes, see [examples.md](examples.md)
