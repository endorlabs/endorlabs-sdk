"""Composable workflow functions for the Endor Labs platform.

Experimental: API may change; not covered by the same stability guarantees
as the rest of the SDK.

Workflows sit between the Client facade (CRUD) and consumer surfaces
(CLI, agents, notebooks). Each function takes a ``Client`` instance,
returns a typed result dataclass, and has no CLI/IO concerns.

Submodules:
    common: Project lookup, shared result types.
    finding_triage: Tag findings, create exception policies.
    notification_setup: Create notification targets and policies.
    semgrep_management: Import/export YAML rules, calibrate rules.
    diagnostics: Compare scan logs, dependency reports.
    platform_setup: Create namespaces, installations, scan profiles.
"""
