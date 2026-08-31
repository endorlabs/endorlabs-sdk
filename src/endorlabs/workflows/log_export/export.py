"""Scheduleable full-row export of PackageFirewallLog and AgentHookEvent."""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.logs.sources import (
    SOURCE_RESOURCE,
    LogSource,
    list_log_events,
    row_to_dict,
)
from endorlabs.workflows.logs.time_window import (
    format_mql_date,
    iter_time_slices,
    parse_iso_utc,
    time_window_filter,
)

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

ExportFormat = Literal["jsonl", "csv"]

# Re-export for callers that imported time helpers from this module.
__all__ = [
    "ExportFormat",
    "LogExportResult",
    "LogMultiExportResult",
    "LogSource",
    "export_logs",
    "export_logs_for_namespaces",
    "format_mql_date",
    "iter_time_slices",
    "parse_iso_utc",
    "row_to_dict",
    "time_window_filter",
]


@dataclass
class LogExportResult(WorkflowResult):
    """Result of a log export run."""

    output_path: str = ""
    row_count: int = 0
    slice_count: int = 0
    source: str = ""
    format: str = ""


def _empty_results() -> list[LogExportResult]:
    return []


@dataclass
class LogMultiExportResult(WorkflowResult):
    """Result of exporting logs for multiple namespaces."""

    source: str = ""
    format: str = ""
    namespace_count: int = 0
    row_count: int = 0
    results: list[LogExportResult] = field(default_factory=_empty_results)


@dataclass
class _ExportState:
    """Mutable counters while writing slices."""

    row_count: int = 0
    slice_count: int = 0


def _combine_filters(*parts: str | None) -> str | None:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    return " and ".join(f"({p})" for p in cleaned)


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
    traverse: bool = False,
) -> LogExportResult:
    """Export full log rows for ``source`` in ``[since, until)`` to a file.

    Rows are written as complete API objects (JSONL) or a CSV ``payload`` column
    holding the JSON object. No field curation is applied.

    Pass ``traverse=True`` when listing from a tenant root whose logs live under
    child namespaces. Prefer density probe + per-NS export for multi-NS pulls.
    """
    if source not in SOURCE_RESOURCE:
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
            rows = list_log_events(
                client,
                source,
                namespace=namespace,
                filter_expr=filter_expr,
                traverse=traverse,
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


def export_logs_for_namespaces(
    client: Client,
    *,
    namespaces: Sequence[str],
    source: LogSource,
    since: datetime | str,
    until: datetime | str,
    output_dir: str | Path,
    export_format: ExportFormat = "jsonl",
    slice_hours: float = 1.0,
    extra_filter: str | None = None,
) -> LogMultiExportResult:
    """Export logs for each namespace into ``output_dir`` (traverse=False)."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    since_dt = parse_iso_utc(since) if isinstance(since, str) else since
    until_dt = parse_iso_utc(until) if isinstance(until, str) else until
    start = since_dt.strftime("%Y%m%dT%H%M%SZ")
    end = until_dt.strftime("%Y%m%dT%H%M%SZ")
    src = source.replace("-", "_")

    results: list[LogExportResult] = []
    errors: list[str] = []
    total_rows = 0
    for ns in namespaces:
        safe = ns.replace("/", "_").replace("\\", "_")
        path = out_dir / f"{safe}-{src}-{start}_{end}.{export_format}"
        result = export_logs(
            client,
            namespace=ns,
            source=source,
            since=since_dt,
            until=until_dt,
            output_path=path,
            export_format=export_format,
            slice_hours=slice_hours,
            extra_filter=extra_filter,
            traverse=False,
        )
        results.append(result)
        total_rows += result.row_count
        if not result.ok:
            errors.extend(result.errors or [result.message])

    failed = sum(1 for r in results if not r.ok)
    if failed and failed == len(results):
        status = "error"
    elif failed:
        status = "partial"
    else:
        status = "success"

    return LogMultiExportResult(
        status=status,
        message=(
            f"Exported {total_rows} {source} row(s) across "
            f"{len(results)} namespace(s) under {out_dir}"
        ),
        errors=errors,
        source=source,
        format=export_format,
        namespace_count=len(results),
        row_count=total_rows,
        results=results,
    )
