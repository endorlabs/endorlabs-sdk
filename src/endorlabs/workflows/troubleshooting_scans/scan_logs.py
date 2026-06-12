"""Compare scan logs across recent ScanResults for a project."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger

from ..common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)


@dataclass
class ScanLogEntry:
    """A single scan run's metadata and log messages."""

    scan_result_uuid: str = ""
    status: str = ""
    exit_code: int | None = None
    start_time: str = ""
    end_time: str = ""
    log_messages: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScanLogComparison(WorkflowResult):
    """Result of comparing multiple scan runs."""

    entries: list[ScanLogEntry] = field(default_factory=list)
    num_scans_requested: int = 0
    num_scans_found: int = 0


def compare_scan_logs(
    client: Client,
    namespace: str,
    project_uuid: str,
    *,
    num_scans: int = 2,
    log_levels: list[str] | None = None,
    _traverse: bool = False,
) -> ScanLogComparison:
    """Compare the last N scan results and their logs for a project."""
    from endorlabs.resources.scan_log_request import ScanLogLevel

    result = ScanLogComparison(num_scans_requested=num_scans)

    scan_results = client.ScanResult.list_by_project(
        project_uuid,
        namespace=namespace,
        limit=num_scans,
    )
    scan_rows = scan_results.values or []

    result.num_scans_found = len(scan_rows)
    if not scan_rows:
        result.message = f"No scan results found for project {project_uuid}."
        return result

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
    if log_levels:
        resolved_levels = [
            level_map[lv.upper()] for lv in log_levels if lv.upper() in level_map
        ]
    else:
        resolved_levels = [ScanLogLevel.ERROR, ScanLogLevel.WARNING]

    for sr in scan_rows[:num_scans]:
        entry = ScanLogEntry(
            scan_result_uuid=sr.uuid,
            status=str(sr.spec.status) if sr.spec and sr.spec.status else "",
            exit_code=sr.spec.exit_code if sr.spec else None,
            start_time=str(sr.spec.start_time)
            if sr.spec and sr.spec.start_time
            else "",
            end_time=str(sr.spec.end_time) if sr.spec and sr.spec.end_time else "",
        )

        try:
            logs = client.ScanResult.get_logs(
                sr.uuid,
                namespace=namespace,
                log_levels=resolved_levels,
            )
            entry.log_messages = [
                {
                    "level": str(msg.level) if msg.level else "",
                    "timestamp": msg.timestamp or "",
                    "payload": msg.json_payload or {},
                }
                for msg in logs
            ]
        except Exception as exc:
            logger.warning("Unable to fetch logs for '%s': %s", sr.uuid, exc)
            entry.log_messages = [{"error": str(exc)}]

        result.entries.append(entry)

    result.message = f"Compared {len(result.entries)}/{num_scans} scan(s)."
    return result
