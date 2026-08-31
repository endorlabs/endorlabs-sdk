"""``endor-log-export`` — scheduleable full-row log dump to JSONL or CSV."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import endorlabs
from endorlabs.context.paths import sanitize_path_segment, task_activity_dir
from endorlabs.workflows.logs.density import (
    probe_log_density,
    probe_result_to_dict,
)

from .export import (
    ExportFormat,
    LogSource,
    export_logs,
    export_logs_for_namespaces,
    parse_iso_utc,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export PackageFirewallLog or AgentHookEvent rows for a time window "
            "to JSONL or CSV (full API objects; no field curation). "
            "Optional per-namespace density probe gates multi-NS pulls."
        ),
    )
    _ = parser.add_argument(
        "-n",
        "--namespace",
        default=None,
        help="Namespace to export from (default: ENDOR_NAMESPACE).",
    )
    _ = parser.add_argument(
        "--source",
        choices=["package-firewall-logs", "policy-violations"],
        default="package-firewall-logs",
        help=(
            "Log source: package-firewall-logs (PackageFirewallLog) or "
            "policy-violations (AgentHookEvent / Agent Governance Policy Violations)."
        ),
    )
    _ = parser.add_argument(
        "--since",
        default=None,
        help="Window start (ISO-8601 UTC). Default: 24h before --until.",
    )
    _ = parser.add_argument(
        "--until",
        default=None,
        help="Window end exclusive (ISO-8601 UTC). Default: now (UTC).",
    )
    _ = parser.add_argument(
        "--format",
        choices=["jsonl", "csv"],
        default="jsonl",
        help="Output format (default: jsonl).",
    )
    _ = parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=(
            f"Output file path (default under "
            f"{task_activity_dir('<namespace>', 'logs').as_posix()}/)."
        ),
    )
    _ = parser.add_argument(
        "--slice-hours",
        type=float,
        default=1.0,
        help="Time-slice width in hours for batched list calls (default: 1).",
    )
    _ = parser.add_argument(
        "--filter",
        default=None,
        help="Optional extra MQL filter combined with the time window.",
    )
    _ = parser.add_argument(
        "--traverse",
        action="store_true",
        help=(
            "Include child namespaces on a single list "
            "(needed when logs live under a child NS)."
        ),
    )
    _ = parser.add_argument(
        "--discover-namespaces",
        action="store_true",
        help=(
            "Discover leaf namespaces under -n, probe density, and export "
            "only namespaces at/above --min-events."
        ),
    )
    _ = parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Run density probe and write JSON summary; do not export rows.",
    )
    _ = parser.add_argument(
        "--min-events",
        type=int,
        default=1,
        help=(
            "Density threshold: namespaces with count >= N need pull "
            "(default: 1; use 0 to export all discovered namespaces)."
        ),
    )
    _ = parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Parallel workers for per-namespace density counts.",
    )
    return parser


def _resolve_namespace(args: argparse.Namespace) -> str:
    ns = args.namespace or os.getenv("ENDOR_NAMESPACE")
    if not ns or not str(ns).strip():
        raise SystemExit(
            "Namespace required: pass -n/--namespace or set ENDOR_NAMESPACE."
        )
    return str(ns).strip()


def _default_output(
    *,
    namespace: str,
    source: str,
    fmt: str,
    since: datetime,
    until: datetime,
) -> Path:
    logs = task_activity_dir(namespace, "logs")
    logs.mkdir(parents=True, exist_ok=True)
    slug = sanitize_path_segment(namespace)
    src = source.replace("-", "_")
    start = since.strftime("%Y%m%dT%H%M%SZ")
    end = until.strftime("%Y%m%dT%H%M%SZ")
    return logs / f"{slug}-{src}-{start}_{end}.{fmt}"


def _default_probe_output(*, namespace: str, source: str) -> Path:
    logs = task_activity_dir(namespace, "logs")
    logs.mkdir(parents=True, exist_ok=True)
    slug = sanitize_path_segment(namespace)
    src = source.replace("-", "_")
    return logs / f"{slug}-{src}-density-probe.json"


def _default_multi_output_dir(*, namespace: str, source: str) -> Path:
    logs = task_activity_dir(namespace, "logs")
    slug = sanitize_path_segment(namespace)
    src = source.replace("-", "_")
    out = logs / f"{slug}-{src}-by-namespace"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _resolve_multi_output_dir(args: argparse.Namespace, *, namespace: str) -> Path:
    if args.output is None:
        return _default_multi_output_dir(namespace=namespace, source=args.source)
    if args.output.suffix in {".jsonl", ".csv", ".json"}:
        return args.output.parent / f"{args.output.stem}-by-namespace"
    return Path(args.output)


def _run_probe_only(
    client: endorlabs.Client,
    args: argparse.Namespace,
    *,
    namespace: str,
    source: LogSource,
    since: datetime,
    until: datetime,
) -> int:
    probe = probe_log_density(
        client,
        source=source,
        root_namespace=namespace,
        since=since,
        until=until,
        min_events=args.min_events,
        max_workers=args.max_workers,
    )
    probe_path = Path(
        args.output or _default_probe_output(namespace=namespace, source=source)
    )
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.write_text(
        json.dumps(probe_result_to_dict(probe), indent=2) + "\n",
        encoding="utf-8",
    )
    print(probe.message)
    print(f"Wrote probe summary to {probe_path}")
    if probe.status == "error":
        for err in probe.errors:
            print(err, file=sys.stderr)
        return 1
    return 0


def _run_discover_export(
    client: endorlabs.Client,
    args: argparse.Namespace,
    *,
    namespace: str,
    source: LogSource,
    since: datetime,
    until: datetime,
    fmt: ExportFormat,
) -> int:
    probe = probe_log_density(
        client,
        source=source,
        root_namespace=namespace,
        since=since,
        until=until,
        min_events=args.min_events,
        max_workers=args.max_workers,
    )
    pull = list(probe.pull_namespaces)
    print(probe.message)
    if not pull:
        print("No namespaces at/above --min-events; skipping export.")
        return 0 if probe.status != "error" else 1

    multi = export_logs_for_namespaces(
        client,
        namespaces=pull,
        source=source,
        since=since,
        until=until,
        output_dir=_resolve_multi_output_dir(args, namespace=namespace),
        export_format=fmt,
        slice_hours=args.slice_hours,
        extra_filter=args.filter,
    )
    print(multi.message)
    if multi.status in {"error", "partial"}:
        for err in multi.errors:
            print(err, file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``endor-log-export``."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        namespace = _resolve_namespace(args)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.probe_only and not args.discover_namespaces:
        args.discover_namespaces = True

    until = parse_iso_utc(args.until) if args.until else datetime.now(tz=UTC)
    since = parse_iso_utc(args.since) if args.since else until - timedelta(hours=24)
    fmt: ExportFormat = args.format
    source: LogSource = args.source

    client = endorlabs.Client(tenant=namespace)
    try:
        if args.probe_only:
            return _run_probe_only(
                client,
                args,
                namespace=namespace,
                source=source,
                since=since,
                until=until,
            )
        if args.discover_namespaces:
            return _run_discover_export(
                client,
                args,
                namespace=namespace,
                source=source,
                since=since,
                until=until,
                fmt=fmt,
            )

        output = args.output or _default_output(
            namespace=namespace,
            source=source,
            fmt=fmt,
            since=since,
            until=until,
        )
        result = export_logs(
            client,
            namespace=namespace,
            source=source,
            since=since,
            until=until,
            output_path=output,
            export_format=fmt,
            slice_hours=args.slice_hours,
            extra_filter=args.filter,
            traverse=args.traverse,
        )
    finally:
        client.close()

    if result.ok:
        print(result.message)
        return 0
    for err in result.errors:
        print(err, file=sys.stderr)
    print(result.message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
