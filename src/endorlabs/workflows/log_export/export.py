"""Scheduleable full-row export of PackageFirewallLog and AgentHookEvent."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from endorlabs.workflows.common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

LogSource = Literal["package-firewall", "agent-hook-events"]
ExportFormat = Literal["jsonl", "csv"]

_SOURCE_RESOURCE: dict[LogSource, str] = {
    "package-firewall": "package-firewall-logs",
    "agent-hook-events": "agent-hook-events",
}


@dataclass
class LogExportResult(WorkflowResult):
    """Result of a log export run."""

    output_path: str = ""
    row_count: int = 0
    slice_count: int = 0
    source: str = ""
    format: str = ""


def _empty_extra() -> dict[str, Any]:
    return {}


@dataclass
class _ExportState:
    """Mutable counters while writing slices."""

    row_count: int = 0
    slice_count: int = 0
    extras: dict[str, Any] = field(default_factory=_empty_extra)


def parse_iso_utc(value: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware UTC datetime."""
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_mql_date(value: datetime) -> str:
    """Format a datetime for Endor MQL ``date(...)`` filters (UTC Z)."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def iter_time_slices(
    since: datetime,
    until: datetime,
    *,
    slice_hours: float = 1.0,
) -> Iterator[tuple[datetime, datetime]]:
    """Yield half-open ``[start, end)`` windows covering ``[since, until)``."""
    if until <= since:
        return
    step = timedelta(hours=slice_hours)
    if step <= timedelta(0):
        raise ValueError("slice_hours must be positive")
    cursor = since
    while cursor < until:
        end = min(cursor + step, until)
        yield cursor, end
        cursor = end


def time_window_filter(since: datetime, until: datetime) -> str:
    """Build an MQL filter for ``meta.create_time`` in ``[since, until)``."""
    return (
        f"meta.create_time >= date({format_mql_date(since)}) and "
        f"meta.create_time < date({format_mql_date(until)})"
    )


def row_to_dict(row: Any) -> dict[str, Any]:
    """Serialize a facade model or dict row to a plain JSON-compatible dict."""
    if isinstance(row, dict):
        return cast("dict[str, Any]", row)
    dump = getattr(row, "model_dump", None)
    if callable(dump):
        data = dump(mode="json", exclude_none=False)
        if isinstance(data, dict):
            return cast("dict[str, Any]", data)
    raise TypeError(f"Unsupported log row type: {type(row)!r}")


def _combine_filters(*parts: str | None) -> str | None:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    return " and ".join(f"({p})" for p in cleaned)


def _list_package_firewall(
    client: Client,
    *,
    namespace: str,
    filter_expr: str | None,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {"namespace": namespace, "traverse": False}
    if filter_expr:
        kwargs["filter"] = filter_expr
    rows = client.PackageFirewallLog.list(**kwargs)
    return [row_to_dict(row) for row in rows]


def _list_agent_hook_events(
    client: Client,
    *,
    namespace: str,
    filter_expr: str | None,
) -> list[dict[str, Any]]:
    api = client._client  # noqa: SLF001 — AgentHookEvent has no facade yet
    if api is None:
        raise RuntimeError("Client has no API transport (closed?)")
    url = f"v1/namespaces/{namespace}/agent-hook-events"
    params: dict[str, Any] = {}
    if filter_expr:
        params["list_parameters.filter"] = filter_expr
    return list(api.get_all(url, params=params))


def _list_source_rows(
    client: Client,
    source: LogSource,
    *,
    namespace: str,
    filter_expr: str | None,
) -> list[dict[str, Any]]:
    if source == "package-firewall":
        return _list_package_firewall(
            client, namespace=namespace, filter_expr=filter_expr
        )
    if source == "agent-hook-events":
        return _list_agent_hook_events(
            client, namespace=namespace, filter_expr=filter_expr
        )
    raise ValueError(f"Unknown source: {source!r}")


def _write_jsonl(path: Path, rows: list[dict[str, Any]], *, append: bool) -> None:
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str))
            handle.write("\n")


def _write_csv(path: Path, rows: list[dict[str, Any]], *, append: bool) -> None:
    mode = "a" if append else "w"
    write_header = not append or not path.exists() or path.stat().st_size == 0
    with path.open(mode, encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["payload"])
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(
                {"payload": json.dumps(row, ensure_ascii=False, default=str)}
            )


def export_logs(
    client: Client,
    *,
    namespace: str,
    source: LogSource,
    since: datetime | str,
    until: datetime | str,
    output_path: str | Path,
    export_format: ExportFormat = "jsonl",
    slice_hours: float = 1.0,
    extra_filter: str | None = None,
) -> LogExportResult:
    """Export full log rows for ``source`` in ``[since, until)`` to a file.

    Rows are written as complete API objects (JSONL) or a CSV ``payload`` column
    holding the JSON object. No field curation is applied.
    """
    if source not in _SOURCE_RESOURCE:
        return LogExportResult(
            status="error",
            message=f"Unsupported source: {source!r}",
            errors=[f"Unsupported source: {source!r}"],
            source=str(source),
            format=export_format,
        )
    since_dt = parse_iso_utc(since) if isinstance(since, str) else since
    until_dt = parse_iso_utc(until) if isinstance(until, str) else until
    if until_dt <= since_dt:
        return LogExportResult(
            status="error",
            message="until must be after since",
            errors=["until must be after since"],
            source=source,
            format=export_format,
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    state = _ExportState()
    try:
        for start, end in iter_time_slices(since_dt, until_dt, slice_hours=slice_hours):
            state.slice_count += 1
            window = time_window_filter(start, end)
            filter_expr = _combine_filters(window, extra_filter)
            rows = _list_source_rows(
                client, source, namespace=namespace, filter_expr=filter_expr
            )
            if not rows:
                continue
            append = state.row_count > 0
            if export_format == "jsonl":
                _write_jsonl(out, rows, append=append)
            elif export_format == "csv":
                _write_csv(out, rows, append=append)
            else:
                raise ValueError(f"Unsupported format: {export_format!r}")
            state.row_count += len(rows)
    except Exception as exc:
        return LogExportResult(
            status="error",
            message=f"Export failed: {exc}",
            errors=[f"{type(exc).__name__}: {exc}"],
            output_path=str(out),
            row_count=state.row_count,
            slice_count=state.slice_count,
            source=source,
            format=export_format,
        )

    if not out.exists():
        # Empty window: still create an empty artifact for schedulers.
        if export_format == "jsonl":
            out.write_text("", encoding="utf-8")
        else:
            with out.open("w", encoding="utf-8", newline="") as handle:
                csv.DictWriter(handle, fieldnames=["payload"]).writeheader()

    return LogExportResult(
        status="success",
        message=(
            f"Exported {state.row_count} {source} row(s) "
            f"across {state.slice_count} slice(s) to {out}"
        ),
        output_path=str(out),
        row_count=state.row_count,
        slice_count=state.slice_count,
        source=source,
        format=export_format,
    )


__all__ = [
    "ExportFormat",
    "LogExportResult",
    "LogSource",
    "export_logs",
    "format_mql_date",
    "iter_time_slices",
    "parse_iso_utc",
    "row_to_dict",
    "time_window_filter",
]
