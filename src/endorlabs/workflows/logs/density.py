"""Per-namespace log density probe (time-window count vs threshold)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from endorlabs.tools.list_bounds import resolve_collect_max_workers
from endorlabs.tools.parallel_scopes import parallel_over
from endorlabs.utils.namespaces import list_probe_namespaces
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.logs.sources import LogSource, count_log_events
from endorlabs.workflows.logs.time_window import parse_iso_utc, time_window_filter

if TYPE_CHECKING:
    from endorlabs.client_surface import Client


def _empty_rows() -> list[NamespaceDensity]:
    return []


def _empty_str_list() -> list[str]:
    return []


@dataclass
class NamespaceDensity:
    """Density measurement for one namespace."""

    namespace: str
    count: int | None = None
    needs_pull: bool = False
    error: str | None = None


@dataclass
class LogDensityProbeResult(WorkflowResult):
    """Result of a multi-namespace log density probe."""

    source: str = ""
    root_namespace: str = ""
    min_events: int = 1
    namespaces_probed: int = 0
    pull_namespaces: list[str] = field(default_factory=_empty_str_list)
    rows: list[NamespaceDensity] = field(default_factory=_empty_rows)
    total_events: int = 0


def probe_log_density(
    client: Client,
    *,
    source: LogSource,
    root_namespace: str,
    since: datetime | str,
    until: datetime | str,
    min_events: int = 1,
    namespaces: Sequence[str] | None = None,
    max_workers: int | None = None,
) -> LogDensityProbeResult:
    """Count log events per namespace in ``[since, until)`` and flag pull candidates.

    Discovers leaf namespaces under ``root_namespace`` unless ``namespaces`` is
    provided. Each namespace is counted with ``traverse=False``. Namespaces with
    ``count >= min_events`` are listed in ``pull_namespaces``.
    """
    if min_events < 0:
        return LogDensityProbeResult(
            status="error",
            message="min_events must be >= 0",
            errors=["min_events must be >= 0"],
            source=source,
            root_namespace=root_namespace,
            min_events=min_events,
        )

    since_dt = parse_iso_utc(since) if isinstance(since, str) else since
    until_dt = parse_iso_utc(until) if isinstance(until, str) else until
    if until_dt <= since_dt:
        return LogDensityProbeResult(
            status="error",
            message="until must be after since",
            errors=["until must be after since"],
            source=source,
            root_namespace=root_namespace,
            min_events=min_events,
        )

    try:
        targets = (
            list(namespaces)
            if namespaces is not None
            else list_probe_namespaces(client, root_namespace)
        )
    except Exception as exc:
        return LogDensityProbeResult(
            status="error",
            message=f"Namespace discovery failed: {exc}",
            errors=[f"{type(exc).__name__}: {exc}"],
            source=source,
            root_namespace=root_namespace,
            min_events=min_events,
        )

    if not targets:
        return LogDensityProbeResult(
            status="success",
            message="No namespaces to probe",
            source=source,
            root_namespace=root_namespace,
            min_events=min_events,
            namespaces_probed=0,
        )

    filt = time_window_filter(since_dt, until_dt)
    workers = resolve_collect_max_workers(max_workers)

    def _probe_one(ns: str) -> NamespaceDensity:
        try:
            count = count_log_events(client, source, namespace=ns, filter_expr=filt)
            return NamespaceDensity(
                namespace=ns,
                count=count,
                needs_pull=count >= min_events,
            )
        except Exception as exc:
            return NamespaceDensity(
                namespace=ns,
                count=None,
                needs_pull=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    rows = list(parallel_over(targets, _probe_one, max_workers=workers))
    # Stable order by input namespace list
    by_ns = {row.namespace: row for row in rows}
    ordered = [by_ns[ns] for ns in targets if ns in by_ns]

    errors = [f"{row.namespace}: {row.error}" for row in ordered if row.error]
    pull = [row.namespace for row in ordered if row.needs_pull]
    total = sum(row.count or 0 for row in ordered)
    failed = sum(1 for row in ordered if row.error)
    if failed and failed == len(ordered):
        status = "error"
    elif failed:
        status = "partial"
    else:
        status = "success"

    return LogDensityProbeResult(
        status=status,
        message=(
            f"Probed {len(ordered)} namespace(s) for {source}: "
            f"{len(pull)} need pull (min_events={min_events}), "
            f"total_events={total}"
        ),
        errors=errors,
        source=source,
        root_namespace=root_namespace,
        min_events=min_events,
        namespaces_probed=len(ordered),
        pull_namespaces=pull,
        rows=ordered,
        total_events=total,
    )


def probe_result_to_dict(result: LogDensityProbeResult) -> dict[str, Any]:
    """Serialize a probe result for JSON CLI output."""
    return {
        "status": result.status,
        "message": result.message,
        "errors": list(result.errors),
        "source": result.source,
        "root_namespace": result.root_namespace,
        "min_events": result.min_events,
        "namespaces_probed": result.namespaces_probed,
        "pull_namespaces": list(result.pull_namespaces),
        "total_events": result.total_events,
        "rows": [
            {
                "namespace": row.namespace,
                "count": row.count,
                "needs_pull": row.needs_pull,
                "error": row.error,
            }
            for row in result.rows
        ],
    }


__all__ = [
    "LogDensityProbeResult",
    "NamespaceDensity",
    "probe_log_density",
    "probe_result_to_dict",
]
