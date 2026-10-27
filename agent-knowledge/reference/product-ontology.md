# SDK ↔ product ontology (glossary)

UI nav labels and CLI/SDK kinds diverge. Prefer product-aligned
`endor-log-export --source` tokens where listed; wire paths may remain kebab
kinds.

| Product / UI phrase | SDK / CLI | Notes |
|---------------------|-----------|-------|
| Package Firewall logs | `--source package-firewall-logs` → `PackageFirewallLog` | Wire path `package-firewall-logs` |
| Package Firewall (VS Code extensions) | `PackageFirewallLog` + `spec.ecosystem=="ECOSYSTEM_VSCODE"` | Same facade; filter example: `endor-log-export -n <tenant> --source package-firewall-logs --filter 'spec.ecosystem=="ECOSYSTEM_VSCODE"'` |
| Policy Violations (Agent Governance) | `--source policy-violations` → `AgentHookEvent` | Wire path stays `agent-hook-events` (x-internal; no facade yet). **Not** Agents Hub Agent Kit call logs. |
| Agents Hub / Agent Kit API call log | `client.AgentTelemetry.activity` / `.calls` / `.iter_calls` | Backend API usage metering (`agent-telemetry`); tenant-safe projection — no request filters in rows |
| Threat Center (Discovery) | `MalwareExposure` / `MalwareExposureQuery` | UI synonym for tenant malware blast-radius; catalog identity still OSS `Malware` / `QueryMalware` |
| Findings | `client.Finding` | Current findings |
| Findings history / burndown | `FindingLog` | Time-series / create-delete trends — not `Finding` |
| Login / SSO auth logs | `AuthenticationLog` | Not `AuditLog` (API audit trail) |
| Malware catalog | `client.Malware` / `QueryMalware` (`scope=oss`) | Coordinate identity |
| Malware exposure (tenant) | `MalwareExposure` / `MalwareExposureQuery` | Customer blast radius (Threat Center) |
