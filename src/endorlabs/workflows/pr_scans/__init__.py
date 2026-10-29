"""Pull-request scan statistics from ``ScanResult`` (time-sharded, parallel).

PR scans are CI-run scans that carry a PR number (``pr=<n>`` tag or
``ScanConfig.SCMPRID``); other CI runs (``merge-to-main`` and similar) are
counted separately and never as PR scans. No ``Finding`` rows are listed.
"""

from endorlabs.workflows.pr_scans.collect import (
    RETENTION_DAYS,
    PrScanStats,
    collect_pr_scan_stats,
    is_blocked,
    pr_number,
    project_clauses,
    time_windows,
)

__all__ = [
    "RETENTION_DAYS",
    "PrScanStats",
    "collect_pr_scan_stats",
    "is_blocked",
    "pr_number",
    "project_clauses",
    "time_windows",
]
