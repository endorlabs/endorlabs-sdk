# Markdown Correctness Review (Tracked Docs)

Date: 2026-04-07

Scope:

- Reviewed all git-tracked Markdown files (`git ls-files "*.md"`).
- Excluded non-tracked caches/context mirrors from correction scope (`.tmp/**`, `.endorlabs-context/**`).
- Prioritized technical/API/command correctness, then local links/paths, then terminology consistency.

## Inventory summary

- Total tracked Markdown files: `50`
- By area:
  - `docs/**`: `30`
  - `.cursor/**`: `12`
  - `.github/**`: `2`
  - `devtools/**`: `2`
  - `src/**`: `1`
  - repo root (`README.md`, `AGENTS.md`, `CONTRIBUTORS.md`): `3`

## Corrections applied

### Critical / major

1. **Broken relative links in high-traffic docs**
   - Fixed in:
     - `docs/contracts.md`
     - `docs/guides/pr-comment-config-and-parallel-comments.md`
   - Result: local markdown link audit now reports `0` broken links across tracked docs.

2. **Incorrect exception namespace guidance**
   - Problem: docs referenced `endorlabs.exceptions` as import/source, but exceptions are exported at top-level `endorlabs` and implemented in `endorlabs.core.exceptions`.
   - Corrected in:
     - `README.md`
     - `docs/contracts.md`
     - `docs/contributing/integration-resource-tests.md` (formerly `resource-implementation.md`)
     - `.github/copilot-instructions.md`
     - `.cursor/skills/endor-implement-sdk-resource/SKILL.md`

3. **Outdated model-sync branch naming**
   - Problem: stale static branch name `chore/model-sync-auto` in contributor workflow docs.
   - Corrected in:
     - `CONTRIBUTORS.md` -> `chore/model-sync-<utc-timestamp>`

### Consistency / clarity

4. **Reference entrypoint for consumers**
   - Updated `docs/reference/README.md` to direct SDK consumers to `README.md` for install/quick start (instead of `AGENTS.md`, which is agent-oriented).

## Validation results

## Link/path validation

- Method: local link/path checker over tracked Markdown links (excluding external URLs and anchor-only links).
- Result: `bad_count = 0`.

## Term/phrase sanity checks

- `endorlabs.exceptions`: no remaining occurrences.
- `chore/model-sync-auto`: no remaining occurrences.

## Remaining backlog (patch sequencing)

No remaining **critical** correctness defects were identified in tracked Markdown after this pass.

Recommended follow-up sequence (minor DX polish):

1. **Terminology normalization**
   - Standardize phrasing for generated vs runtime surfaces (e.g., "generated contract", "runtime registry adapter") across `docs/contracts.md`, `docs/README.md`, and `AGENTS.md`.
2. **Command style normalization**
   - Prefer one canonical "recommended model-sync command" block in each maintainer-facing doc and cross-link to `devtools/sync/README.md`.
3. **Automated docs checks in CI**
   - Optional future hardening: add a markdown/link checker job for tracked docs to prevent link regressions.

## Evidence files checked first (high-risk set)

- `README.md`
- `AGENTS.md`
- `CONTRIBUTORS.md`
- `docs/contracts.md`
- `docs/contributing/docs-drift-workflow.md`
- `devtools/sync/README.md`
- `docs/reference/README.md`
- `docs/guides/retrieving-scan-results.md`
