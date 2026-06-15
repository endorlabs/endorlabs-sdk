"""Composable workflow functions for the Endor Labs platform.

Experimental: API may change; not covered by the same stability guarantees
as the rest of the SDK.

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
    notifications: Notification targets and policies.
    platform: Namespaces, installations, scan profiles, auth policies.
    reachability: PV/finding reachability context and stitched evidence helpers.
    relationships: Project relationship graph helpers.
    analytics: Estate DependencyMetadata aggregates and tabular exports.
    semgrep: Semgrep rule import/export, calibration, metadata inventory.
    troubleshooting_scans: Scan result/log triage scripts (CLI-oriented).
"""
