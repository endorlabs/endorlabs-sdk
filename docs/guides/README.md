# Guides

SDK how-to and workflows.

- [consumer-ux-list-update.md](consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- List performance (scope, traverse, debugging): [rules-of-engagement/list-query-performance.md](../rules-of-engagement/list-query-performance.md).
- [pr-comment-config-and-parallel-comments.md](pr-comment-config-and-parallel-comments.md) — Endor findings → GitHub pull request review comments in CI; historical PRCommentConfig notes.
- [retrieving-scan-results.md](retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.
- [self-validation-scorecard-and-replay.md](self-validation-scorecard-and-replay.md) — Deterministic scorecards, nightly artifacts, and replay-friendly snapshots.

**Scan regression troubleshooting:** Agent skill [.cursor/skills/troubleshooting-scans/](../../.cursor/skills/troubleshooting-scans/); parameterized scripts in [`scripts/troubleshooting_scans/`](../../scripts/troubleshooting_scans/). Related: [list-query-performance.md](../rules-of-engagement/list-query-performance.md), [troubleshooting.md](../rules-of-engagement/troubleshooting.md).

## Custom SAST Rules

End-to-end workflow for threat modeling, authoring, and deploying custom OpenGrep/Semgrep rules into the Endor Labs platform. Canonical docs live in the Agent Skill: [.cursor/skills/custom-sast-rules/](../../.cursor/skills/custom-sast-rules/). See the skill's `THREAT_MODEL.md`, `AUTHORING.md`, `SYNTAX_REFERENCE.md`, and `IMPORT_EXPORT.md`.
