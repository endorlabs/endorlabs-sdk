# Reachability Provenance Examples

## Example 1: Reachable dependency, unreachable function

### Input signals

- Finding tags include:
  - `FINDING_TAGS_REACHABLE_DEPENDENCY`
  - `FINDING_TAGS_UNREACHABLE_FUNCTION`
- Summary says no vulnerable function is known reachable.
- Call graph shows application calls into a risky API surface of the affected package.

### Triage outcome

- Dependency reachability: reachable
- Function reachability (strict `affected_callpath_uris`): unreachable
- Practical risk signal: present
- Likely disconnect: structured vulnerable callpath mapping is narrower than observed reachable API surface
- Next action: review `oss` vulnerability `affected_callpath_uris` and signature normalization rules

---

## Example 2: CVE/GHSA alias fragmentation

### Input signals

- CVE record in `oss` has ecosystem/version coverage but no `affected_callpath_uris`.
- GHSA alias in `oss` has `SOURCE_ENDOR` entry with structured callpaths.
- Finding behavior aligns with one alias but not the other.

### Triage outcome

- Alias consistency: fragmented
- Primary provenance source: GHSA alias with `SOURCE_ENDOR`
- Likely disconnect: alias-level enrichment mismatch in vulnerability provenance
- Next action: ensure canonical alias resolution returns a fully enriched affected entry for evaluation

---

## Example 3: Signature format mismatch

### Input signals

- `affected_callpath_uris` exist and appear semantically relevant.
- Call graph contains equivalent methods with different URI/signature representation.
- Strict function matching returns unknown or unreachable.

### Triage outcome

- Dependency reachability: reachable
- Function reachability (strict): unknown/unreachable
- Practical risk signal: present
- Likely disconnect: URI canonicalization or signature normalization mismatch
- Next action: improve normalization before strict callpath comparison
