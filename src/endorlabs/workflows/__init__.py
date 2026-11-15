"""Composable workflow functions for the Endor Labs platform.

**Departing at v1.0.0:** This package (CLIs, reports, estate, exports) will leave
the core ``endorlabs`` wheel as a breaking change. A successor distribution
(``endorlabs-workflows``) will be released before removal. Through 0.x these
modules remain importable but are **not** semver-protected — only ``Client`` /
``APIClient`` and resource facades are. See the changelog and README API
stability notes.

Workflows sit between the Client facade (CRUD) and consumer surfaces
(CLI, agents, notebooks). Each function takes a ``Client`` instance,
returns a typed result dataclass, and has no CLI/IO concerns (except
dedicated ``*.cli`` entry modules).

Subpackages:
    common: Project lookup, shared result types.
    agent_context: Project context bundles, session markdown artifacts.
    callgraph: Call graph export and local decoded-graph search.
    dependencies: Dependency metadata reports and visibility.
    findings: Finding triage and exception policies.
    logs: Log resource group-by-time aggregation helpers.
    notifications: Notification targets and policies.
    platform: Namespaces, installations, scan profiles, auth policies.
    reachability: PV/finding reachability context and stitched evidence helpers.
    estate: Estate analytics, cardinality, dashboard counts, topology.
    reports: Tenant report analyze → export → bundle workflows (``endor-reports``).
    semgrep: Semgrep rule import/export, calibration, metadata inventory.
    troubleshooting_scans: Scan result/log triage scripts (CLI-oriented).
    log_export: Scheduleable PackageFirewallLog / AgentHookEvent file dumps.
    license_export: MAIN-context DependencyMetadata + SPDX license join for CI.
    findings_export: MAIN-context Finding JSONL export for CI.
"""
