"""Troubleshooting scan workflow — library surface for composition.

CLI-oriented step scripts live in sibling modules; this package re-exports
stable helpers for session scripts. Experimental API.
"""

from __future__ import annotations

from endorlabs.utils.namespace import resource_namespace
from endorlabs.utils.serialization import object_to_dict, to_json_dict
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.troubleshooting_scans.common import (
    load_json,
    match_projects,
    write_json,
)
from endorlabs.workflows.troubleshooting_scans.diff_scans import compute_diff
from endorlabs.workflows.troubleshooting_scans.scan_error_hits import (
    ScanErrorHitsEvidence,
    search_embedded_scan_errors,
)
from endorlabs.workflows.troubleshooting_scans.scan_logs_evidence import (
    ScanLogsEvidence,
    acquire_scan_logs,
)
from endorlabs.workflows.troubleshooting_scans.scan_pair_evidence import (
    ScanPairEvidenceResult,
    ScanRoleEvidence,
    acquire_scan_pair_evidence,
    assemble_scan_pair_evidence,
)
from endorlabs.workflows.troubleshooting_scans.scan_results_evidence import (
    ScanResultsEvidence,
    acquire_scan_results,
)

# Compat alias: prefer ``resource_namespace`` in new code.
project_namespace = resource_namespace

__all__ = [
    "ScanErrorHitsEvidence",
    "ScanLogsEvidence",
    "ScanPairEvidenceResult",
    "ScanResultsEvidence",
    "ScanRoleEvidence",
    "WorkflowResult",
    "acquire_scan_logs",
    "acquire_scan_pair_evidence",
    "acquire_scan_results",
    "assemble_scan_pair_evidence",
    "compute_diff",
    "load_json",
    "match_projects",
    "object_to_dict",
    "project_namespace",
    "resource_namespace",
    "search_embedded_scan_errors",
    "to_json_dict",
    "write_json",
]
