#!/usr/bin/env python3
r"""Compare Scan Logs Maneuver.

A repeatable script for comparing the last N scan results and their logs for a project,
helping users troubleshoot scan errors by highlighting differences between runs.

This maneuver fetches recent ScanResults for a project, retrieves detailed logs via
ScanLogRequest, and outputs a comparison report showing status, exit codes, and errors.

Example::

    uv run python maneuvers/compare_scan_logs.py \
      --namespace "endor-solutions-tgowan" \
      --repository-url "https://github.com/org/repo.git" \
      --num-scans 2 \
      --traverse

Filter Syntax Note:
    For substring matching, use ``matches`` with regex.
    The ``contains`` operator is for array fields only.

"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endorlabs.api_client import APIClient
from endorlabs.resources import project, scan_result
from endorlabs.resources.scan_log_request import (
    CreateScanLogRequestPayload,
    ScanLogLevel,
    ScanLogRequestMetaCreate,
    ScanLogRequestSpecCreate,
    create_scan_log_request,
)
from endorlabs.types import ListParameters

# Import common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from common.project_lookup import find_project_by_repository_url

# Configure logging to reduce verbosity
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("endorlabs").setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Log levels to include by default
DEFAULT_LOG_LEVELS = [ScanLogLevel.ERROR, ScanLogLevel.WARNING]


def parse_log_levels(levels_str: str) -> list[ScanLogLevel]:
    """Parse comma-separated log level string into ScanLogLevel enums."""
    levels = []
    for level in levels_str.split(","):
        level = level.strip().upper()
        try:
            # Map shorthand names to enum values
            level_map = {
                "ERROR": ScanLogLevel.ERROR,
                "WARNING": ScanLogLevel.WARNING,
                "INFO": ScanLogLevel.INFO,
                "DEBUG": ScanLogLevel.DEBUG,
                "CRITICAL": ScanLogLevel.CRITICAL,
                "ALERT": ScanLogLevel.ALERT,
                "EMERGENCY": ScanLogLevel.EMERGENCY,
                "NOTICE": ScanLogLevel.NOTICE,
            }
            if level in level_map:
                levels.append(level_map[level])
            else:
                logger.warning(f"Unknown log level: {level}, skipping")
        except (KeyError, ValueError):
            logger.warning(f"Invalid log level: {level}, skipping")
    return levels if levels else DEFAULT_LOG_LEVELS


def find_project(
    client: APIClient,
    namespace: str,
    repository_url: str | None = None,
    project_uuid: str | None = None,
    traverse: bool = False,
) -> tuple[str | None, str | None]:
    """Find project by UUID or repository URL.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        repository_url: Repository URL to search for
        project_uuid: Direct project UUID
        traverse: Whether to search child namespaces

    Returns:
        Tuple of (project_uuid, project_name) or (None, None) if not found.

    """
    if project_uuid:
        # If UUID provided, get project to confirm it exists and get name
        try:
            proj = project.get_project(client, namespace, project_uuid)
            if proj:
                return proj.uuid, proj.meta.name if proj.meta else None
        except Exception as e:
            logger.warning(f"Could not get project by UUID {project_uuid}: {e}")
            # Try with traverse if enabled
            if traverse:
                list_params = ListParameters(
                    filter=f'uuid == "{project_uuid}"',
                    traverse=True,
                )
                projects = project.list_projects(client, namespace, list_params)
                if projects:
                    proj = projects[0]
                    return proj.uuid, proj.meta.name if proj.meta else None
        return project_uuid, None  # Return UUID even if we can't get details

    if repository_url:
        # Use the common lookup utility first (handles various URL formats)
        found_uuid = find_project_by_repository_url(client, namespace, repository_url)
        if found_uuid:
            # Get project details
            try:
                proj = project.get_project(client, namespace, found_uuid)
                if proj:
                    return proj.uuid, proj.meta.name if proj.meta else None
            except Exception:
                pass
            return found_uuid, repository_url

        # If common lookup fails and traverse is enabled, try with traverse
        if traverse:
            logger.info("Trying with traverse enabled...")
            # Try exact match with traverse
            list_params = ListParameters(
                filter=f'meta.name == "{repository_url}"',
                traverse=True,
            )
            projects = project.list_projects(client, namespace, list_params)
            if projects:
                proj = projects[0]
                return proj.uuid, proj.meta.name if proj.meta else None

            # Try matches (regex) for substring with traverse
            # Escape special regex characters in URL
            escaped_url = repository_url.replace(".", r"\.").replace("/", r"\/")
            list_params = ListParameters(
                filter=f'meta.name matches ".*{escaped_url}.*"',
                traverse=True,
            )
            projects = project.list_projects(client, namespace, list_params)
            if projects:
                proj = projects[0]
                return proj.uuid, proj.meta.name if proj.meta else None

    return None, None


def get_recent_scan_results(
    client: APIClient,
    namespace: str,
    project_uuid: str,
    num_scans: int = 2,
    traverse: bool = False,
) -> list[Any]:
    """Get the most recent scan results for a project.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        project_uuid: Project UUID to filter by
        num_scans: Number of scan results to retrieve
        traverse: Whether to search child namespaces

    Returns:
        List of ScanResult objects, sorted by create_time descending.

    """
    try:
        # Build filter for project UUID (scan results use meta.parent_uuid)
        filter_expr = f'meta.parent_uuid == "{project_uuid}"'

        list_params = ListParameters(
            filter=filter_expr,
            sort_field="meta.create_time",
            sort_order="desc",
            page_size=num_scans,
            traverse=traverse,
        )

        results = scan_result.list_scan_results(
            client, namespace, list_params, max_pages=1
        )
        logger.info(f"Found {len(results)} scan results for project {project_uuid}")
        return results[:num_scans]

    except Exception as e:
        logger.error(f"Error retrieving scan results: {e}")
        return []


def get_scan_logs(
    client: APIClient,
    namespace: str,
    scan_result_uuid: str,
    log_levels: list[ScanLogLevel],
    max_entries: int = 500,
) -> list[Any]:
    """Retrieve logs for a specific scan result.

    Args:
        client: Authenticated APIClient instance
        namespace: Namespace that owns the scan result
        scan_result_uuid: UUID of the scan result
        log_levels: Log levels to filter by
        max_entries: Maximum number of log entries

    Returns:
        List of log messages.

    """
    try:
        payload = CreateScanLogRequestPayload(
            meta=ScanLogRequestMetaCreate(name=f"compare-logs-{scan_result_uuid[:8]}"),
            spec=ScanLogRequestSpecCreate(
                max_entries=max_entries,
                scan_result_uuid=scan_result_uuid,
                log_levels=log_levels,
                newest_first=True,
            ),
        )

        request = create_scan_log_request(client, namespace, payload)
        if request.spec and request.spec.log_messages:
            return request.spec.log_messages
        return []

    except Exception as e:
        logger.warning(f"Could not retrieve logs for scan {scan_result_uuid}: {e}")
        return []


def calculate_duration(start_time: str | None, end_time: str | None) -> str:
    """Calculate human-readable duration between two timestamps."""
    if not start_time or not end_time:
        return "N/A"

    try:
        # Parse ISO format timestamps
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        delta = end - start

        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    except (ValueError, TypeError):
        return "N/A"


def format_log_message(log_msg: Any) -> str:
    """Format a log message for display."""
    level = str(log_msg.level).replace("LOG_LEVEL_", "") if log_msg.level else "UNKNOWN"

    # Extract message from json_payload
    message = ""
    if log_msg.json_payload:
        # Common message fields in log payloads
        message = (
            log_msg.json_payload.get("message")
            or log_msg.json_payload.get("msg")
            or log_msg.json_payload.get("error")
            or str(log_msg.json_payload)
        )

    timestamp = log_msg.timestamp[:19] if log_msg.timestamp else ""
    return f"[{level}] {timestamp}: {message}"


def format_full_log_entry(log_msg: Any) -> str:
    """Format a log message with full JSON payload for verbose output.

    Output format matches endorctl log format:
    {timestamp} {LEVEL}: {message}
    {
      "json_payload": ...
    }
    """
    level = str(log_msg.level).replace("LOG_LEVEL_", "") if log_msg.level else "UNKNOWN"

    # Extract primary message from json_payload
    message = ""
    if log_msg.json_payload:
        message = (
            log_msg.json_payload.get("message")
            or log_msg.json_payload.get("msg")
            or log_msg.json_payload.get("error")
            or log_msg.json_payload.get("status", "")[:100]
            or ""
        )

    # Format timestamp for header (convert ISO to readable)
    timestamp = ""
    if log_msg.timestamp:
        try:
            dt = datetime.fromisoformat(log_msg.timestamp.replace("Z", "+00:00"))
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            timestamp = log_msg.timestamp[:19]

    # Build the full entry
    header = f"{timestamp} {level}: {message}"

    # Format JSON payload with indentation
    payload_dict: dict[str, Any] = {}
    if log_msg.tags:
        payload_dict["tags"] = log_msg.tags
    if log_msg.timestamp:
        payload_dict["timestamp"] = log_msg.timestamp
    if log_msg.json_payload:
        payload_dict.update(log_msg.json_payload)

    json_block = json.dumps(payload_dict, indent=2, default=str)

    return f"{header}\n{json_block}"


def export_full_logs(
    scan_result_uuid: str,
    logs: list[Any],
    output_dir: str,
) -> str:
    """Export full logs for a scan result to a file.

    Args:
        scan_result_uuid: UUID of the scan result
        logs: List of log messages
        output_dir: Directory to write log files

    Returns:
        Path to the exported file

    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    filename = f"scan-result_{scan_result_uuid}_logs.txt"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        for log_msg in logs:
            entry = format_full_log_entry(log_msg)
            f.write(entry)
            f.write("\n")

    return filepath


def generate_text_report(
    project_name: str | None,
    project_uuid: str,
    namespace: str,
    scans_data: list[dict[str, Any]],
) -> str:
    """Generate a text-formatted comparison report."""
    lines = []
    lines.append("=" * 60)
    lines.append("SCAN COMPARISON REPORT")
    lines.append("=" * 60)
    lines.append(f"Project: {project_name or project_uuid}")
    lines.append(f"Namespace: {namespace}")
    lines.append(f"Scans compared: {len(scans_data)}")
    lines.append("")

    for i, scan_data in enumerate(scans_data, 1):
        scan = scan_data["scan"]
        logs = scan_data["logs"]

        lines.append("-" * 60)
        label = "(most recent)" if i == 1 else ""
        lines.append(f"SCAN {i} {label}")
        lines.append("-" * 60)
        lines.append(f"UUID: {scan.uuid}")

        # Status and exit code
        status = str(scan.spec.status) if scan.spec and scan.spec.status else "UNKNOWN"
        status = status.replace("STATUS_", "")
        lines.append(f"Status: {status}")

        exit_code = (
            str(scan.spec.exit_code) if scan.spec and scan.spec.exit_code else "UNKNOWN"
        )
        exit_code = exit_code.replace("ENDORCTL_RC_", "")
        lines.append(f"Exit Code: {exit_code}")

        # Timing
        start_time = scan.spec.start_time if scan.spec else None
        end_time = scan.spec.end_time if scan.spec else None
        duration = calculate_duration(start_time, end_time)

        if start_time:
            lines.append(f"Started: {start_time}")
        if end_time:
            lines.append(f"Ended: {end_time}")
        lines.append(f"Duration: {duration}")

        # Languages detected
        if scan.spec and scan.spec.languages_detected:
            lines.append(f"Languages: {', '.join(scan.spec.languages_detected)}")

        # Inline logs from scan result
        if scan.spec and scan.spec.logs:
            lines.append("")
            lines.append(f"Inline Logs ({len(scan.spec.logs)}):")
            lines.extend(
                f"  - {log[:200]}..." for log in scan.spec.logs[:10]
            )  # Limit to first 10, truncate long messages

        # Detailed logs from ScanLogRequest
        if logs:
            error_logs = [
                log
                for log in logs
                if log.level
                in [ScanLogLevel.ERROR, ScanLogLevel.CRITICAL, ScanLogLevel.ALERT]
            ]
            warning_logs = [log for log in logs if log.level == ScanLogLevel.WARNING]

            lines.append("")
            lines.append(f"Errors ({len(error_logs)}):")
            if error_logs:
                lines.extend(
                    f"  - {format_log_message(log)[:200]}" for log in error_logs[:20]
                )  # Limit display
            else:
                lines.append("  (none)")

            lines.append("")
            lines.append(f"Warnings ({len(warning_logs)}):")
            if warning_logs:
                lines.extend(
                    f"  - {format_log_message(log)[:200]}" for log in warning_logs[:10]
                )  # Limit display
            else:
                lines.append("  (none)")
        else:
            lines.append("")
            lines.append("Detailed Logs: (not available)")

        lines.append("")

    # Comparison section
    if len(scans_data) >= 2:
        lines.append("=" * 60)
        lines.append("DIFFERENCES")
        lines.append("=" * 60)

        scan1 = scans_data[0]["scan"]
        scan2 = scans_data[1]["scan"]

        status1 = (
            str(scan1.spec.status).replace("STATUS_", "")
            if scan1.spec and scan1.spec.status
            else "UNKNOWN"
        )
        status2 = (
            str(scan2.spec.status).replace("STATUS_", "")
            if scan2.spec and scan2.spec.status
            else "UNKNOWN"
        )

        if status1 != status2:
            lines.append(f"- Status changed: {status2} -> {status1}")

        exit1 = (
            str(scan1.spec.exit_code).replace("ENDORCTL_RC_", "")
            if scan1.spec and scan1.spec.exit_code
            else "UNKNOWN"
        )
        exit2 = (
            str(scan2.spec.exit_code).replace("ENDORCTL_RC_", "")
            if scan2.spec and scan2.spec.exit_code
            else "UNKNOWN"
        )

        if exit1 != exit2:
            lines.append(f"- Exit code changed: {exit2} -> {exit1}")

        # Compare error counts
        errors1 = len(
            [
                log
                for log in scans_data[0]["logs"]
                if log.level
                in [ScanLogLevel.ERROR, ScanLogLevel.CRITICAL, ScanLogLevel.ALERT]
            ]
        )
        errors2 = len(
            [
                log
                for log in scans_data[1]["logs"]
                if log.level
                in [ScanLogLevel.ERROR, ScanLogLevel.CRITICAL, ScanLogLevel.ALERT]
            ]
        )

        if errors1 != errors2:
            change = "increased" if errors1 > errors2 else "decreased"
            lines.append(f"- Error count {change}: {errors2} -> {errors1}")

        if status1 == status2 and exit1 == exit2 and errors1 == errors2:
            lines.append("- No significant differences detected between scans")

        lines.append("")

    return "\n".join(lines)


def generate_json_report(
    project_name: str | None,
    project_uuid: str,
    namespace: str,
    scans_data: list[dict[str, Any]],
) -> str:
    """Generate a JSON-formatted comparison report."""
    report = {
        "project": {
            "uuid": project_uuid,
            "name": project_name,
        },
        "namespace": namespace,
        "scans_compared": len(scans_data),
        "scans": [],
    }

    for i, scan_data in enumerate(scans_data):
        scan = scan_data["scan"]
        logs = scan_data["logs"]

        scan_report = {
            "index": i + 1,
            "uuid": scan.uuid,
            "status": str(scan.spec.status) if scan.spec and scan.spec.status else None,
            "exit_code": (
                str(scan.spec.exit_code) if scan.spec and scan.spec.exit_code else None
            ),
            "start_time": scan.spec.start_time if scan.spec else None,
            "end_time": scan.spec.end_time if scan.spec else None,
            "duration": calculate_duration(
                scan.spec.start_time if scan.spec else None,
                scan.spec.end_time if scan.spec else None,
            ),
            "languages_detected": (scan.spec.languages_detected if scan.spec else None),
            "inline_logs": scan.spec.logs if scan.spec else None,
            "error_count": len(
                [
                    log
                    for log in logs
                    if log.level
                    in [ScanLogLevel.ERROR, ScanLogLevel.CRITICAL, ScanLogLevel.ALERT]
                ]
            ),
            "warning_count": len(
                [log for log in logs if log.level == ScanLogLevel.WARNING]
            ),
            "errors": [
                {
                    "level": str(log.level) if log.level else None,
                    "timestamp": log.timestamp,
                    "message": log.json_payload,
                }
                for log in logs
                if log.level
                in [ScanLogLevel.ERROR, ScanLogLevel.CRITICAL, ScanLogLevel.ALERT]
            ][:20],  # Limit
            "warnings": [
                {
                    "level": str(log.level) if log.level else None,
                    "timestamp": log.timestamp,
                    "message": log.json_payload,
                }
                for log in logs
                if log.level == ScanLogLevel.WARNING
            ][:10],  # Limit
        }
        report["scans"].append(scan_report)

    return json.dumps(report, indent=2, default=str)


def main() -> None:
    """Compare scan logs with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare recent scan results and logs to troubleshoot scan errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare last 2 scans by git URL
  uv run python maneuvers/compare_scan_logs.py \\
    --namespace "endor-solutions-tgowan" \\
    --repository-url "https://github.com/org/repo.git" \\
    --num-scans 2 \\
    --traverse

  # Compare last 3 scans by project UUID
  uv run python maneuvers/compare_scan_logs.py \\
    --namespace "endor-solutions-tgowan" \\
    --project-uuid "697c16c370eac368e62c6dff" \\
    --num-scans 3 \\
    --log-levels "ERROR,WARNING,INFO"

  # Dry run to see what would be fetched
  uv run python maneuvers/compare_scan_logs.py \\
    --namespace "endor-solutions-tgowan" \\
    --repository-url "https://github.com/org/repo.git" \\
    --dry-run

  # Output as JSON
  uv run python maneuvers/compare_scan_logs.py \\
    --namespace "endor-solutions-tgowan" \\
    --project-uuid "abc123" \\
    --output-format json
        """,
    )

    # Required arguments
    parser.add_argument(
        "--namespace",
        required=True,
        help="Target namespace to search in",
    )

    # Project identification (at least one required)
    project_group = parser.add_argument_group(
        "Project Identification",
        "Specify how to identify the project (at least one required)",
    )
    project_group.add_argument(
        "--repository-url",
        help="Repository URL (e.g., 'https://github.com/org/repo.git')",
    )
    project_group.add_argument(
        "--project-uuid",
        help="Direct project UUID",
    )

    # Optional arguments
    parser.add_argument(
        "--num-scans",
        type=int,
        default=2,
        help="Number of recent scans to compare (default: 2)",
    )
    parser.add_argument(
        "--log-levels",
        default="ERROR,WARNING",
        help="Comma-separated log levels to include (default: ERROR,WARNING). "
        "Options: ERROR, WARNING, INFO, DEBUG, CRITICAL, ALERT, EMERGENCY, NOTICE",
    )
    parser.add_argument(
        "--traverse",
        action="store_true",
        help="Include child namespaces in search",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without making API calls for logs",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--export-dir",
        help="Directory to export full log files (enables full log export). "
        "Each scan result gets a file: scan-result_{uuid}_logs.txt",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("endorlabs").setLevel(logging.DEBUG)

    # Validate arguments
    if not args.project_uuid and not args.repository_url:
        parser.error(
            "At least one of --project-uuid or --repository-url must be specified"
        )

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Find project
        logger.info("Finding project...")
        project_uuid, project_name = find_project(
            client=client,
            namespace=args.namespace,
            repository_url=args.repository_url,
            project_uuid=args.project_uuid,
            traverse=args.traverse,
        )

        if not project_uuid:
            logger.error(
                f"Could not find project. "
                f"Repository URL: {args.repository_url}, "
                f"Project UUID: {args.project_uuid}"
            )
            print(
                "ERROR: Project not found. "
                "Try using --traverse to search child namespaces."
            )
            sys.exit(1)

        logger.info(f"Found project: {project_name or project_uuid}")

        # Get recent scan results
        logger.info(f"Fetching last {args.num_scans} scan results...")
        scan_results = get_recent_scan_results(
            client=client,
            namespace=args.namespace,
            project_uuid=project_uuid,
            num_scans=args.num_scans,
            traverse=args.traverse,
        )

        if not scan_results:
            print(f"No scan results found for project {project_name or project_uuid}")
            print("The project may not have been scanned yet.")
            sys.exit(0)

        logger.info(f"Found {len(scan_results)} scan results")

        if args.dry_run:
            print("=== DRY RUN - Scans that would be compared ===")
            print(f"Project: {project_name or project_uuid}")
            print(f"Namespace: {args.namespace}")
            print(f"Number of scans: {len(scan_results)}")
            print()
            for i, scan in enumerate(scan_results, 1):
                status = (
                    str(scan.spec.status).replace("STATUS_", "")
                    if scan.spec and scan.spec.status
                    else "UNKNOWN"
                )
                print(f"{i}. UUID: {scan.uuid}")
                print(f"   Status: {status}")
                print(f"   Created: {scan.meta.create_time if scan.meta else 'N/A'}")
                print()
            return

        # Parse log levels for report filtering
        report_log_levels = parse_log_levels(args.log_levels)
        logger.info(f"Report log levels: {[str(lvl) for lvl in report_log_levels]}")

        # When exporting, fetch ALL log levels with more entries
        export_mode = args.export_dir is not None
        if export_mode:
            # All standard log levels for full export
            all_log_levels = [
                ScanLogLevel.DEBUG,
                ScanLogLevel.INFO,
                ScanLogLevel.NOTICE,
                ScanLogLevel.WARNING,
                ScanLogLevel.ERROR,
                ScanLogLevel.CRITICAL,
                ScanLogLevel.ALERT,
                ScanLogLevel.EMERGENCY,
            ]
            fetch_levels = all_log_levels
            fetch_max_entries = 5000  # API maximum
            logger.info(f"Export mode: all levels, max {fetch_max_entries} entries")
        else:
            fetch_levels = report_log_levels
            fetch_max_entries = 500

        # Fetch logs for each scan
        scans_data = []
        exported_files: list[str] = []
        for scan in scan_results:
            # Get namespace from scan result (may differ from parent namespace)
            scan_namespace = (
                scan.tenant_meta.namespace
                if scan.tenant_meta and scan.tenant_meta.namespace
                else args.namespace
            )

            logger.info(f"Fetching logs for scan {scan.uuid}...")
            logs = get_scan_logs(
                client=client,
                namespace=scan_namespace,
                scan_result_uuid=scan.uuid,
                log_levels=fetch_levels,
                max_entries=fetch_max_entries,
            )

            # Export full logs if requested
            if export_mode and logs:
                export_path = export_full_logs(
                    scan_result_uuid=scan.uuid,
                    logs=logs,
                    output_dir=args.export_dir,
                )
                exported_files.append(export_path)
                logger.info(f"Exported {len(logs)} log entries to: {export_path}")

            # Filter logs for report (if we fetched all levels for export)
            if export_mode:
                # Filter to report levels for summary
                filtered_logs = [log for log in logs if log.level in report_log_levels]
            else:
                filtered_logs = logs

            scans_data.append(
                {
                    "scan": scan,
                    "logs": filtered_logs,
                    "total_logs": len(logs),
                }
            )

        # Generate report
        if args.output_format == "json":
            report = generate_json_report(
                project_name=project_name,
                project_uuid=project_uuid,
                namespace=args.namespace,
                scans_data=scans_data,
            )
        else:
            report = generate_text_report(
                project_name=project_name,
                project_uuid=project_uuid,
                namespace=args.namespace,
                scans_data=scans_data,
            )

        print(report)

        # Show exported files
        if exported_files:
            print()
            print("=" * 60)
            print("EXPORTED LOG FILES")
            print("=" * 60)
            for filepath in exported_files:
                print(f"  {filepath}")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
