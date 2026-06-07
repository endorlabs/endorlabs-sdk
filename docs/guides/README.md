# Guides

SDK how-to and workflows.

- [examples.md](examples.md) — Skill walkthrough and minimal API snippets for a first tenant session.
- [consumer-ux-list-update.md](consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- List performance (scope, traverse, debugging): [contributing/list-query-performance.md](../contributing/list-query-performance.md).
- [pr-comment-config-and-parallel-comments.md](pr-comment-config-and-parallel-comments.md) — Endor findings → GitHub pull request review comments in CI; historical PRCommentConfig notes.
- [retrieving-scan-results.md](retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.
- [pypi-publication-draft.md](pypi-publication-draft.md) — Draft: hatch-vcs tag policy, local `uv build` verification, TestPyPI → PyPI rollout (not yet automated).
- [testpypi-readiness-assessment.md](testpypi-readiness-assessment.md) — Initial TestPyPI readiness report (v0.1.0 release state).

**Scan regression troubleshooting:** Agent skill [.cursor/skills/endor-troubleshooting-scans/](../../.cursor/skills/endor-troubleshooting-scans/); workflows in `endorlabs.workflows.troubleshooting_scans` (e.g. `python -m endorlabs.workflows.troubleshooting_scans.run_troubleshooting_workflow`). Related: [list-query-performance.md](../contributing/list-query-performance.md), [troubleshooting.md](../contributing/troubleshooting.md).

## Custom SAST Rules

End-to-end workflow for threat modeling, authoring, and deploying custom OpenGrep/Semgrep rules into the Endor Labs platform. Canonical docs live in the Agent Skill: [.cursor/skills/endor-custom-sast-rules/](../../.cursor/skills/endor-custom-sast-rules/). See the skill's `THREAT_MODEL.md`, `AUTHORING.md`, `SYNTAX_REFERENCE.md`, and `IMPORT_EXPORT.md`.
