"""``endor-log-export`` — scheduleable full-row log dump to JSONL or CSV."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment

from .export import ExportFormat, LogSource, export_logs, parse_iso_utc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export PackageFirewallLog or AgentHookEvent rows for a time window "
            "to JSONL or CSV (full API objects; no field curation)."
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
        choices=["package-firewall", "agent-hook-events"],
        default="package-firewall",
        help="Log source to export (default: package-firewall).",
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
        help="Output file path (default under workspace/runs/log-export/).",
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
    runs = default_runs_dir("log-export")
    runs.mkdir(parents=True, exist_ok=True)
    slug = sanitize_path_segment(namespace)
    src = source.replace("-", "_")
    start = since.strftime("%Y%m%dT%H%M%SZ")
    end = until.strftime("%Y%m%dT%H%M%SZ")
    return runs / f"{slug}-{src}-{start}_{end}.{fmt}"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``endor-log-export``."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        namespace = _resolve_namespace(args)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    until = parse_iso_utc(args.until) if args.until else datetime.now(tz=UTC)
    since = parse_iso_utc(args.since) if args.since else until - timedelta(hours=24)
    fmt: ExportFormat = args.format
    source: LogSource = args.source
    output = args.output or _default_output(
        namespace=namespace,
        source=source,
        fmt=fmt,
        since=since,
        until=until,
    )

    client = endorlabs.Client(tenant=namespace)
    try:
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
