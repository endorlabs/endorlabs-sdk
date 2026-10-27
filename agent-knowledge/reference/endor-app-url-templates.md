# Structured Endor app hyperlinks

When relaying customer-facing or RCA evidence, **cite Endor app URLs first**, then
local artifact paths only when critical (for example a triage JSON under
`.endorlabs/tasks/…`). Analytics and full SCA share the same URL shapes — the
scan UUID distinguishes them. Parsers:
`endorlabs.workflows.troubleshooting_scans.parse_endor_app_url`.

| Resource | Template |
|----------|----------|
| Project | `https://app.endorlabs.com/t/<namespace>/projects/<project-uuid>` |
| Scan history | `https://app.endorlabs.com/t/<namespace>/scan-history/<scan-result-uuid>` |
| Finding | `https://app.endorlabs.com/t/<namespace>/projects/<project-uuid>/findings/<finding-uuid>` |
| Package inventory | `https://app.endorlabs.com/t/<namespace>/projects/<project-uuid>/versions/default/inventory/packages` |

Use placeholders (`<namespace>`, `<project-uuid>`, `<scan-result-uuid>`,
`<finding-uuid>`) in skills and docs — never commit estate identifiers.

For SDK/API validation playbooks, load **`skills/endor-troubleshoot-sdk/SKILL.md`**
and [`validation-reference.md`](../skills/endor-troubleshoot-sdk/validation-reference.md).
Repo clone only: `docs/contributing/troubleshooting.md` (not shipped in the wheel).
