"""Scan-pair evidence assembly for host injection.

Pure ``assemble_scan_pair_evidence`` needs no network. ``acquire_scan_pair_evidence``
fetches via an injected ``Client`` then assembles — still no filesystem writes.

Optional scope / parent / window / order checks mirror the Foundry TEMP SDK-007
shim intent without cloning Foundry projection types. Host cancel/deadline
errors always propagate (fail closed) rather than becoming data ``status=error``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, cast

from endorlabs.core.exceptions import DeadlineExceededError, RequestCancelledError
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


class ScanPairValidationError(ValueError):
    """Stable rejection for scope/parent/window/order mismatches."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


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
    rejection_code: str | None = None


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


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ScanPairValidationError("invalid_timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ScanPairValidationError("invalid_timestamp") from exc
    if parsed.tzinfo is None:
        raise ScanPairValidationError("timestamp_requires_timezone")
    return parsed


def _nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        typed = cast("dict[str, Any]", cur)
        cur = typed.get(key)
    return cur


def _reject_row_scope_mismatch(
    row: dict[str, Any],
    *,
    namespace: str,
    project_uuid: str | None,
) -> None:
    row_ns = _nested(row, "tenant_meta", "namespace")
    if row_ns is not None and row_ns != namespace:
        raise ScanPairValidationError("resource_scope_mismatch")
    if project_uuid is not None:
        parent = _nested(row, "meta", "parent_uuid")
        if parent is not None and parent != project_uuid:
            raise ScanPairValidationError("scan_project_mismatch")


def validate_scan_pair_scope(
    *,
    namespace: str,
    primary: dict[str, Any],
    secondary: dict[str, Any],
    project_uuid: str | None = None,
    repository_url: str | None = None,
    project: dict[str, Any] | None = None,
    window_from: str | None = None,
    window_to: str | None = None,
    require_primary_in_window: bool = False,
) -> None:
    """Reject mismatched scope, parent, repository, window, or time order.

    ``primary`` is the selected/newer scan; ``secondary`` is previous/older when
    order is checked. Raises ``ScanPairValidationError`` with a stable ``code``.
    """
    primary_uuid = primary.get("uuid")
    secondary_uuid = secondary.get("uuid")
    if (
        isinstance(primary_uuid, str)
        and isinstance(secondary_uuid, str)
        and primary_uuid == secondary_uuid
    ):
        raise ScanPairValidationError("scan_roles_require_distinct_ids")

    for row in (primary, secondary):
        _reject_row_scope_mismatch(row, namespace=namespace, project_uuid=project_uuid)

    if project is not None and repository_url is not None:
        clone = _nested(project, "spec", "git", "http_clone_url")
        if clone is not None and clone != repository_url:
            raise ScanPairValidationError("repository_identity_mismatch")

    primary_start = _nested(primary, "spec", "start_time")
    secondary_start = _nested(secondary, "spec", "start_time")
    if (
        primary_start is not None
        and secondary_start is not None
        and _parse_time(secondary_start) >= _parse_time(primary_start)
    ):
        raise ScanPairValidationError("previous_scan_not_older")

    if window_from is not None and window_to is not None and require_primary_in_window:
        begin, finish = _parse_time(window_from), _parse_time(window_to)
        if primary_start is None:
            raise ScanPairValidationError("selected_scan_outside_failed_window")
        start = _parse_time(primary_start)
        if not (begin <= start < finish):
            raise ScanPairValidationError("selected_scan_outside_failed_window")


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
    namespace: str | None = None,
    project_uuid: str | None = None,
    repository_url: str | None = None,
    project: dict[str, Any] | None = None,
    window_from: str | None = None,
    window_to: str | None = None,
    require_primary_in_window: bool = False,
    validate_scope: bool = False,
) -> ScanPairEvidenceResult:
    """Assemble pair roles, log outcomes, and field diff from caller-supplied rows.

    ``concurrent`` must be supplied by the caller when known. ``None`` leaves
    concurrency as ``unknown`` — historical log text alone must not imply
    currently running scans.

    When ``validate_scope`` is True (or any scope/window args are supplied),
    runs ``validate_scan_pair_scope`` before assembly.
    """
    should_validate = validate_scope or any(
        x is not None
        for x in (project_uuid, repository_url, project, window_from, window_to)
    )
    if should_validate:
        if not namespace:
            raise ScanPairValidationError("invalid_namespace")
        validate_scan_pair_scope(
            namespace=namespace,
            primary=primary,
            secondary=secondary,
            project_uuid=project_uuid,
            repository_url=repository_url,
            project=project,
            window_from=window_from,
            window_to=window_to,
            require_primary_in_window=require_primary_in_window,
        )

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


def _reraise_host_lifetime(exc: BaseException) -> None:
    if isinstance(exc, (RequestCancelledError, DeadlineExceededError)):
        raise exc


def acquire_scan_pair_evidence(
    client: Client,
    *,
    namespace: str,
    primary_scan_result_uuid: str,
    secondary_scan_result_uuid: str,
    selection_reason: str = "caller_supplied",
    concurrent: bool | None = None,
    fetch_logs: bool = False,
    project_uuid: str | None = None,
    repository_url: str | None = None,
    project: dict[str, Any] | None = None,
    window_from: str | None = None,
    window_to: str | None = None,
    require_primary_in_window: bool = False,
    validate_scope: bool = False,
) -> ScanPairEvidenceResult:
    """Fetch primary/secondary ScanResult rows and assemble typed pair evidence.

    Log payloads are left ``unknown`` unless ``fetch_logs`` is True (then uses
    ``ScanResult.get_logs``; acquisition errors become ``primary_log_outcome`` /
    ``secondary_log_outcome`` ``error``). Host cancel/deadline errors are
    re-raised. Concurrency is never inferred.
    """
    try:
        primary = fetch_scan_result(client, namespace, primary_scan_result_uuid)
        secondary = fetch_scan_result(client, namespace, secondary_scan_result_uuid)
    except Exception as exc:
        _reraise_host_lifetime(exc)
        raise

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
            _reraise_host_lifetime(exc)
            primary_log_error = f"{type(exc).__name__}: {exc}"
        try:
            secondary_logs = [
                str(x)
                for x in client.ScanResult.get_logs(
                    secondary_scan_result_uuid, namespace=namespace
                )
            ]
        except Exception as exc:
            _reraise_host_lifetime(exc)
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
        namespace=namespace,
        project_uuid=project_uuid,
        repository_url=repository_url,
        project=project,
        window_from=window_from,
        window_to=window_to,
        require_primary_in_window=require_primary_in_window,
        validate_scope=validate_scope,
    )
