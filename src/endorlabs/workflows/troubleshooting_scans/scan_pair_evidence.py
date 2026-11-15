"""Scan-pair evidence assembly for host injection.

Pure ``assemble_scan_pair_evidence`` needs no network. ``acquire_scan_pair_evidence``
fetches via an injected ``Client`` then assembles — still no filesystem writes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.troubleshooting_scans.diff_scans import (
    compute_diff,
    fetch_scan_result,
)
from endorlabs.workflows.troubleshooting_scans.scan_summaries import (
    scan_result_metrics,
    scanlog_entries_have_content,
)

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

LogOutcome = Literal["ok", "empty", "error", "partial", "unknown"]
ConcurrencyEvidence = Literal["concurrent", "not_concurrent", "unknown"]


def _empty_dict() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class ScanRoleEvidence:
    """One side of a scan pair with identity and observed status/time."""

    uuid: str | None
    status: Any
    create_time: str | None
    role: Literal["primary", "secondary"]


@dataclass
class ScanPairEvidenceResult(WorkflowResult):
    """Typed pair evidence; concurrency never inferred from log text alone."""

    primary: ScanRoleEvidence | None = None
    secondary: ScanRoleEvidence | None = None
    selection_reason: str = ""
    concurrency: ConcurrencyEvidence = "unknown"
    primary_log_outcome: LogOutcome = "unknown"
    secondary_log_outcome: LogOutcome = "unknown"
    diff: dict[str, Any] = field(default_factory=_empty_dict)


def _role_from_scan(
    scan: dict[str, Any],
    *,
    role: Literal["primary", "secondary"],
) -> ScanRoleEvidence:
    metrics = scan_result_metrics(scan)
    uuid_raw = metrics.get("uuid")
    uuid = str(uuid_raw) if isinstance(uuid_raw, str) and uuid_raw else None
    create_raw = metrics.get("create_time")
    create_time = create_raw if isinstance(create_raw, str) else None
    return ScanRoleEvidence(
        uuid=uuid,
        status=metrics.get("status"),
        create_time=create_time,
        role=role,
    )


def _log_outcome(
    logs: Sequence[str] | dict[str, Any] | None,
    *,
    log_error: str | None,
) -> LogOutcome:
    if log_error:
        return "error"
    if logs is None:
        return "unknown"
    if isinstance(logs, dict):
        if logs.get("error"):
            return "error"
        entries_raw = logs.get("entries")
        if entries_raw is None and "messages" in logs:
            entries_raw = logs.get("messages")
        if not isinstance(entries_raw, list):
            return "partial" if logs else "empty"
        typed_entries = cast("list[Any]", entries_raw)
        entries = [str(x) for x in typed_entries]
    else:
        entries = [str(x) for x in logs]
    if not entries:
        return "empty"
    if scanlog_entries_have_content(entries):
        return "ok"
    return "partial"


def assemble_scan_pair_evidence(
    primary: dict[str, Any],
    secondary: dict[str, Any],
    *,
    selection_reason: str = "caller_supplied",
    primary_logs: Sequence[str] | dict[str, Any] | None = None,
    secondary_logs: Sequence[str] | dict[str, Any] | None = None,
    primary_log_error: str | None = None,
    secondary_log_error: str | None = None,
    concurrent: bool | None = None,
) -> ScanPairEvidenceResult:
    """Assemble pair roles, log outcomes, and field diff from caller-supplied rows.

    ``concurrent`` must be supplied by the caller when known. ``None`` leaves
    concurrency as ``unknown`` — historical log text alone must not imply
    currently running scans.
    """
    primary_role = _role_from_scan(primary, role="primary")
    secondary_role = _role_from_scan(secondary, role="secondary")
    if concurrent is True:
        concurrency: ConcurrencyEvidence = "concurrent"
    elif concurrent is False:
        concurrency = "not_concurrent"
    else:
        concurrency = "unknown"

    primary_log = _log_outcome(primary_logs, log_error=primary_log_error)
    secondary_log = _log_outcome(secondary_logs, log_error=secondary_log_error)
    diff = compute_diff(primary, secondary)

    warnings: list[str] = []
    if primary_log in {"empty", "error", "partial", "unknown"}:
        warnings.append(f"primary_log_outcome={primary_log}")
    if secondary_log in {"empty", "error", "partial", "unknown"}:
        warnings.append(f"secondary_log_outcome={secondary_log}")
    if concurrency == "unknown":
        warnings.append("concurrency=unknown")

    status = "partial" if warnings else "success"
    message = (
        "Scan pair evidence assembled with unknowns or log gaps."
        if warnings
        else "Scan pair evidence assembled."
    )
    return ScanPairEvidenceResult(
        status=status,
        message=message,
        errors=[],
        primary=primary_role,
        secondary=secondary_role,
        selection_reason=selection_reason,
        concurrency=concurrency,
        primary_log_outcome=primary_log,
        secondary_log_outcome=secondary_log,
        diff=diff,
    )


def acquire_scan_pair_evidence(
    client: Client,
    *,
    namespace: str,
    primary_scan_result_uuid: str,
    secondary_scan_result_uuid: str,
    selection_reason: str = "caller_supplied",
    concurrent: bool | None = None,
    fetch_logs: bool = False,
) -> ScanPairEvidenceResult:
    """Fetch primary/secondary ScanResult rows and assemble typed pair evidence.

    Log payloads are left ``unknown`` unless ``fetch_logs`` is True (then uses
    ``ScanResult.get_logs``; acquisition errors become ``primary_log_outcome`` /
    ``secondary_log_outcome`` ``error``). Concurrency is never inferred.
    """
    primary = fetch_scan_result(client, namespace, primary_scan_result_uuid)
    secondary = fetch_scan_result(client, namespace, secondary_scan_result_uuid)
    primary_logs: list[str] | None = None
    secondary_logs: list[str] | None = None
    primary_log_error: str | None = None
    secondary_log_error: str | None = None
    if fetch_logs:
        try:
            primary_logs = [
                str(x)
                for x in client.ScanResult.get_logs(
                    primary_scan_result_uuid, namespace=namespace
                )
            ]
        except Exception as exc:
            primary_log_error = f"{type(exc).__name__}: {exc}"
        try:
            secondary_logs = [
                str(x)
                for x in client.ScanResult.get_logs(
                    secondary_scan_result_uuid, namespace=namespace
                )
            ]
        except Exception as exc:
            secondary_log_error = f"{type(exc).__name__}: {exc}"

    return assemble_scan_pair_evidence(
        primary,
        secondary,
        selection_reason=selection_reason,
        primary_logs=primary_logs,
        secondary_logs=secondary_logs,
        primary_log_error=primary_log_error,
        secondary_log_error=secondary_log_error,
        concurrent=concurrent,
    )
