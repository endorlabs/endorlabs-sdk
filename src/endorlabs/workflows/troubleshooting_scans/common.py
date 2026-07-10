"""Shared helpers for troubleshooting scan workflows (re-export barrel).

Prefer importing from :mod:`artifacts`, :mod:`collect`, or :mod:`scan_summaries`
directly in new code.
"""

from __future__ import annotations

import argparse

from endorlabs.utils.serialization import object_to_dict, to_json_dict
from endorlabs.workflows.troubleshooting_scans.artifacts import (
    RUN_BUCKET,
    build_filename,
    default_troubleshooting_output_dir,
    iso_now_compact,
    root_tenant,
    sanitize_segment,
    write_json,
    write_text,
)
from endorlabs.workflows.troubleshooting_scans.collect import (
    match_projects,
    parallel_collect_for_projects,
)
from endorlabs.workflows.troubleshooting_scans.scan_summaries import (
    date_window_from_bounds,
    date_window_from_days,
    load_json,
    parse_app_scan_history_url,
    parse_endor_app_url,
    scan_result_extended_summary,
    scan_result_metrics,
    scanlog_entries_have_content,
    scanlog_line,
    scanlog_line_has_content,
    summarize_environment_config,
)

__all__ = [
    "RUN_BUCKET",
    "build_filename",
    "date_window_from_bounds",
    "date_window_from_days",
    "default_troubleshooting_output_dir",
    "iso_now_compact",
    "load_json",
    "match_projects",
    "object_to_dict",
    "parallel_collect_for_projects",
    "parse_app_scan_history_url",
    "parse_common_args",
    "parse_endor_app_url",
    "root_tenant",
    "sanitize_segment",
    "scan_result_extended_summary",
    "scan_result_metrics",
    "scanlog_entries_have_content",
    "scanlog_line",
    "scanlog_line_has_content",
    "summarize_environment_config",
    "to_json_dict",
    "write_json",
    "write_text",
]


def parse_common_args(description: str) -> argparse.ArgumentParser:
    """Build parser with common options used by all scripts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--tenant", required=True, help="Target namespace/tenant root")
    parser.add_argument(
        "--output-dir",
        default=default_troubleshooting_output_dir(),
        help=(
            "Directory for generated artifacts "
            f"(default: {default_troubleshooting_output_dir()})"
        ),
    )
    parser.add_argument(
        "--timestamped",
        action="store_true",
        help="Append timestamp suffix to output filenames",
    )
    parser.add_argument(
        "--strict-filename-contract",
        action="store_true",
        default=True,
        help="Enforce rootTenant__objectKind__objectUuid naming (default: true)",
    )
    return parser
