# Guides

SDK how-to and workflows.

- [consumer-ux-list-update.md](consumer-ux-list-update.md) — Filter vs mask vs update_mask; flat kwargs; spec-driven UX.
- [retrieving-scan-results.md](retrieving-scan-results.md) — Project → ScanResult → Finding; traverse and field-mask.

## Custom SAST Rules

End-to-end workflow for threat modeling, authoring, and deploying custom OpenGrep/Semgrep rules into the Endor Labs platform. Also available as an Agent Skill: [.cursor/skills/custom-sast-rules/](../../.cursor/skills/custom-sast-rules/).

- [threat-modeling-for-sast-rules.md](threat-modeling-for-sast-rules.md) — CWE Top 25 checklist, first-principles questions, absence-detection patterns for SDKs and client libraries.
- [authoring-opengrep-rules.md](authoring-opengrep-rules.md) — From threat-model finding to validated YAML rule; pattern strategies, metavariable unification, validation loop.
- [opengrep-rule-syntax-reference.md](opengrep-rule-syntax-reference.md) — Compact syntax card for rule YAML with Endor Labs metadata extensions and do/don't table.
- [importing-semgrep-rules-into-endor.md](importing-semgrep-rules-into-endor.md) — Import/export maneuver usage, SDK types, API constraints, and verification with endorctl.
