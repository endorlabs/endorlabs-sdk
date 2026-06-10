# Guides

SDK how-to and workflows for **consumers** of the package.

- [examples.md](examples.md) — Skill walkthrough and minimal API snippets for a first tenant session.
- [consumer-ux-list-update.md](consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; SDK consumer UX.
- [retrieving-scan-results.md](retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.
- List performance (scope, traverse, debugging): [contributing/list-query-performance.md](../contributing/list-query-performance.md).

**Scan regression troubleshooting:** Agent skill [endor-troubleshooting-scans](../../agent-knowledge/skills/endor-troubleshooting-scans/SKILL.md) (optional Cursor mirror: `.cursor/skills/endor-troubleshooting-scans/`); workflows in `endorlabs.workflows.troubleshooting_scans`. Related: [list-query-performance.md](../contributing/list-query-performance.md), [troubleshooting.md](../contributing/troubleshooting.md).

## Custom SAST Rules

End-to-end workflow for threat modeling, authoring, and deploying custom OpenGrep/Semgrep rules into the Endor Labs platform. Canonical docs: [endor-custom-sast-rules](../../agent-knowledge/skills/endor-custom-sast-rules/SKILL.md) (`THREAT_MODEL.md`, `AUTHORING.md`, `SYNTAX_REFERENCE.md`, `IMPORT_EXPORT.md`). Optional Cursor mirror: `.cursor/skills/endor-custom-sast-rules/`.

Maintainer topics (release CI, PR comment wiring, estate migration): [contributing/README.md](../contributing/README.md).
