"""Scan log acquisition for host injection (SDK-006 / SDK-007).

``acquire_scan_logs`` paginates ``ScanResult.get_logs`` via an injected
``Client`` and returns typed evidence without filesystem writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from endorlabs.workflows.common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

LogOutcome = Literal["ok", "empty", "error", "partial", "unknown"]


def _empty_messages() -> list[dict[str, Any]]:
    return []


@dataclass
class ScanLogsEvidence(WorkflowResult):
    """Typed scan-log window; no artifact paths."""

    scan_result_uuid: str = ""
    owner_namespace: str = ""
    start_time: str | None = None
    end_time: str | None = None
    rounds: int = 0
    messages: list[dict[str, Any]] = field(default_factory=_empty_messages)
    log_outcome: LogOutcome = "unknown"
    detail: str = ""

    @property
    def count(self) -> int:
        """Number of de-duplicated log messages."""
        return len(self.messages)


def iso_to_dt(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware UTC datetime."""
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)


def dt_to_iso(value: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC string with ``Z`` suffix."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _dedupe_key(message: Any) -> tuple[str | None, str]:
    payload = getattr(message, "json_payload", None)
    payload_s = (
        json.dumps(payload, sort_keys=True, ensure_ascii=True) if payload else ""
    )
    return getattr(message, "timestamp", None), payload_s


def message_to_dict(message: Any) -> dict[str, Any]:
    """Normalize one ScanLog message to a plain dict."""
    return {
        "timestamp": getattr(message, "timestamp", None),
        "level": (
            getattr(getattr(message, "level", None), "value", None)
            or str(getattr(message, "level", "") or "")
        ),
        "json_payload": getattr(message, "json_payload", None),
        "tags": getattr(message, "tags", None),
    }


def iter_scan_log_batches(
    client: Client,
    *,
    namespace: str,
    scan_result_uuid: str,
    batch_size: int = 500,
    max_rounds: int = 50,
    start_time: str | None = None,
    end_time: str | None = None,
) -> tuple[list[Any], int]:
    """Paginate ``get_logs`` with a moving start_time cursor.

    Returns the de-duplicated message list and the number of fetch rounds.
    """
    cursor = start_time
    seen: set[tuple[str | None, str]] = set()
    all_messages: list[Any] = []
    rounds = 0

    while rounds < max_rounds:
        rounds += 1
        batch = client.ScanResult.get_logs(
            scan_result_uuid,
            namespace=namespace,
            max_entries=batch_size,
            start_time=cursor,
            end_time=end_time,
            newest_first=False,
        )
        if not batch:
            break

        new_count = 0
        last_ts: str | None = None
        for message in batch:
            last_ts = getattr(message, "timestamp", last_ts)
            key = _dedupe_key(message)
            if key in seen:
                continue
            seen.add(key)
            all_messages.append(message)
            new_count += 1

        if new_count == 0:
            break
        if len(batch) < batch_size or not last_ts:
            break

        cursor = dt_to_iso(iso_to_dt(last_ts) + timedelta(milliseconds=1))

    return all_messages, rounds


def acquire_scan_logs(
    client: Client,
    *,
    scan_result_uuid: str,
    namespace: str,
    batch_size: int = 500,
    max_rounds: int = 50,
    start_time: str | None = None,
    end_time: str | None = None,
) -> ScanLogsEvidence:
    """Fetch a bounded scan-log window for one scan result UUID.

    Does not invent concurrency or "running now" from log text. Empty batches
    yield ``log_outcome="empty"``; capped rounds with remaining pages yield
    ``partial``.
    """
    from endorlabs.core.exceptions import DeadlineExceededError, RequestCancelledError

    effective_end = end_time or dt_to_iso(datetime.now(UTC))
    try:
        messages, rounds = iter_scan_log_batches(
            client,
            namespace=namespace,
            scan_result_uuid=scan_result_uuid,
            batch_size=batch_size,
            max_rounds=max_rounds,
            start_time=start_time,
            end_time=effective_end,
        )
    except (RequestCancelledError, DeadlineExceededError):
        # Host lifetime errors fail closed — never fold into data status=error.
        raise
    except Exception as exc:
        return ScanLogsEvidence(
            status="error",
            message=str(exc),
            errors=[str(exc)],
            scan_result_uuid=scan_result_uuid,
            owner_namespace=namespace,
            start_time=start_time,
            end_time=effective_end,
            rounds=0,
            messages=[],
            log_outcome="error",
            detail=str(exc),
        )

    rows = [message_to_dict(m) for m in messages]
    if not rows:
        outcome: LogOutcome = "empty"
        detail = "No log messages in the requested window."
        status = "success"
    elif rounds >= max_rounds:
        outcome = "partial"
        detail = f"Stopped after max_rounds={max_rounds}."
        status = "partial"
    else:
        outcome = "ok"
        detail = ""
        status = "success"

    return ScanLogsEvidence(
        status=status,
        message=detail,
        scan_result_uuid=scan_result_uuid,
        owner_namespace=namespace,
        start_time=start_time,
        end_time=effective_end,
        rounds=rounds,
        messages=rows,
        log_outcome=outcome,
        detail=detail,
    )
