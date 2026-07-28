"""Unified CLI for tenant and namespace report workflows."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import endorlabs
from endorlabs.context.paths import default_runs_dir, sanitize_path_segment
from endorlabs.workflows.reports.bundles.executive_packet import build_report_packet
from endorlabs.workflows.reports.export.html.render import (
    default_packet_output_dir,
    render_report_packet,
)
from endorlabs.workflows.reports.parity import compare_packet_cube
from endorlabs.workflows.reports.schemas.packet_v0 import RUN_BUCKET


def _add_namespace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-n",
        "--namespace",
        required=True,
        help="Tenant or namespace root (e.g. example-tenant).",
    )


def _packet_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    packet = sub.add_parser(
        "packet",
        help="Build and render the executive HTML report packet.",
    )
    _add_namespace(packet)
    packet.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Output directory for HTML + cube "
            f"(default: .endorlabs-context/workspace/runs/{RUN_BUCKET}/"
            "<namespace>-executive-packet/)."
        ),
    )
    packet.add_argument("--lookback", type=int, default=13)
    packet.add_argument(
        "--min-projects",
        type=int,
        default=1,
        help=(
            "Display filter: omit tag series with fewer than this many tagged "
            "projects (default: 1 = all tags with series)."
        ),
    )
    packet.add_argument(
        "--workers",
        type=int,
        default=24,
        help="Parallel FindingLog matrix pulls for tagged projects (default: 24).",
    )
    packet.add_argument("--skip-version-sprawl", action="store_true")
    packet.add_argument("--skip-findings-burndown", action="store_true")
    packet.add_argument("--timeout", type=float, default=900.0)
    return packet


def _parity_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parity = sub.add_parser(
        "parity",
        help="Build packet and compare metrics to scratch baseline JSON files.",
    )
    _add_namespace(parity)
    parity.add_argument(
        "--baseline-adoption",
        type=Path,
        default=None,
        help="Scratch adoption canvas JSON (or ENDOR_VALIDATE_ADOPTION_CUBE).",
    )
    parity.add_argument(
        "--baseline-sprawl",
        type=Path,
        default=None,
        help="Scratch version-cardinality cube JSON (or ENDOR_VALIDATE_VC_CUBE).",
    )
    parity.add_argument(
        "--baseline-burndown",
        type=Path,
        default=None,
        help="Scratch findings-burndown cube JSON (or ENDOR_VALIDATE_BURNDOWN_CUBE).",
    )
    parity.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Parity run directory "
            "(default: workspace/runs/report-parity/<tenant>-<YYYYMMDD>/)."
        ),
    )
    parity.add_argument("--lookback", type=int, default=13)
    parity.add_argument(
        "--min-projects",
        type=int,
        default=1,
        help="Display filter for tag series (default: 1).",
    )
    parity.add_argument(
        "--workers",
        type=int,
        default=24,
        help="Parallel FindingLog matrix pulls for tagged projects (default: 24).",
    )
    parity.add_argument("--skip-version-sprawl", action="store_true")
    parity.add_argument("--skip-findings-burndown", action="store_true")
    parity.add_argument("--timeout", type=float, default=900.0)
    return parity


def _tenant_report_parser(
    sub: argparse._SubParsersAction,
    name: str,
    help_text: str,
) -> argparse.ArgumentParser:
    parser = sub.add_parser(name, help=help_text)
    _add_namespace(parser)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace/runs/<bucket>/).",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="endor-reports",
        description="Endor Labs tenant and namespace report workflows.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _packet_parser(sub)
    _parity_parser(sub)
    _tenant_report_parser(sub, "duplicates", "Find duplicate project registrations.")
    _tenant_report_parser(
        sub, "cli-vs-cloud", "Classify CLI vs cloud project registrations."
    )
    _tenant_report_parser(
        sub, "login-count", "AuthenticationLog login counts by identity."
    )
    _tenant_report_parser(sub, "credential-expiry", "Credential expiry horizon report.")
    _tenant_report_parser(
        sub, "auth-policies", "Audit AuthorizationPolicy claim forms."
    )
    _tenant_report_parser(
        sub, "ci-endorctl", "Audit CI endorctl versions from scan metadata."
    )

    findings = sub.add_parser(
        "findings-trend",
        help="FindingLog weekly new-vs-resolved chart (JSON + optional canvas).",
    )
    _add_namespace(findings)
    findings.add_argument("--output-dir", type=Path, default=None)
    findings.add_argument("--canvas-dir", type=Path, default=None)
    findings.add_argument("--interval", default="week")
    findings.add_argument("--lookback", type=int, default=13)
    findings.add_argument("--analysis-only", action="store_true")
    findings.add_argument("--skip-canvas", action="store_true")

    prf = sub.add_parser(
        "prf-analysis",
        help="Potentially reachable findings analysis (JSON + canvas + PDF).",
    )
    _add_namespace(prf)
    prf.add_argument("--output-dir", type=Path, default=None)
    prf.add_argument("--canvas-dir", type=Path, default=None)
    prf.add_argument("--chrome", type=Path, default=None)
    prf.add_argument("--skip-canvas", action="store_true")
    prf.add_argument("--skip-pdf", action="store_true")
    prf.add_argument("--html-only", action="store_true")
    prf.add_argument("--analysis-only", action="store_true")
    return parser


def _default_parity_dir(namespace: str) -> Path:
    slug = sanitize_path_segment(namespace)
    day = datetime.now(UTC).strftime("%Y%m%d")
    return default_runs_dir("report-parity") / f"{slug}-{day}"


def _run_packet(args: argparse.Namespace) -> int:
    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else default_packet_output_dir(args.namespace)
    )
    client = endorlabs.Client(tenant=args.namespace, timeout=float(args.timeout))
    try:
        cube = build_report_packet(
            client,
            args.namespace,
            lookback=int(args.lookback),
            min_projects=int(args.min_projects),
            max_workers=int(args.workers),
            include_version_sprawl=not args.skip_version_sprawl,
            include_findings_burndown=not args.skip_findings_burndown,
        )
    finally:
        client.close()
    written = render_report_packet(cube, out_dir)
    print(f"Wrote report packet to {out_dir}")
    for path in written:
        rel = path.name if path.parent == out_dir else path.relative_to(out_dir)
        print(f"  {rel}")
    return 0


def _run_parity(args: argparse.Namespace) -> int:
    adoption = args.baseline_adoption or os.getenv("ENDOR_VALIDATE_ADOPTION_CUBE")
    sprawl = args.baseline_sprawl or os.getenv("ENDOR_VALIDATE_VC_CUBE")
    burndown = args.baseline_burndown or os.getenv("ENDOR_VALIDATE_BURNDOWN_CUBE")
    missing = [
        name
        for name, value in (
            ("--baseline-adoption / ENDOR_VALIDATE_ADOPTION_CUBE", adoption),
            ("--baseline-sprawl / ENDOR_VALIDATE_VC_CUBE", sprawl),
            ("--baseline-burndown / ENDOR_VALIDATE_BURNDOWN_CUBE", burndown),
        )
        if not value
    ]
    if missing:
        print("Missing baseline paths:", ", ".join(missing), file=sys.stderr)
        return 2

    out_root = (
        Path(args.output_dir)
        if args.output_dir
        else _default_parity_dir(args.namespace)
    )
    packet_dir = out_root / "packet"
    packet_dir.mkdir(parents=True, exist_ok=True)

    client = endorlabs.Client(tenant=args.namespace, timeout=float(args.timeout))
    try:
        cube = build_report_packet(
            client,
            args.namespace,
            lookback=int(args.lookback),
            min_projects=int(args.min_projects),
            max_workers=int(args.workers),
            include_version_sprawl=not args.skip_version_sprawl,
            include_findings_burndown=not args.skip_findings_burndown,
        )
    finally:
        client.close()
    render_report_packet(cube, packet_dir)

    baseline_adoption = json.loads(Path(adoption).read_text(encoding="utf-8"))
    baseline_sprawl = json.loads(Path(sprawl).read_text(encoding="utf-8"))
    baseline_burndown = json.loads(Path(burndown).read_text(encoding="utf-8"))
    report = compare_packet_cube(
        cube,
        baseline_adoption=baseline_adoption,
        baseline_sprawl=baseline_sprawl,
        baseline_burndown=baseline_burndown,
    )
    summary_path = out_root / "compare-summary.json"
    summary_path.write_text(
        json.dumps(report.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote packet to {packet_dir}")
    print(f"Wrote parity summary to {summary_path}")
    print(f"Parity ok: {report.ok}")
    for row in report.rows:
        status = "ok" if row.within_tolerance else "FAIL"
        delta = f"{row.delta_pct:.2f}%" if row.delta_pct is not None else "n/a"
        print(
            f"  [{status}] {row.metric}: new={row.new} prior={row.prior} delta={delta}"
        )
    return 0 if report.ok else 1


def _tenant_hint_argv(args: argparse.Namespace) -> list[str]:
    argv = ["--tenant-hint", args.namespace]
    if args.output is not None:
        argv.extend(["--output-dir", str(args.output)])
    return argv


def _tenant_argv(args: argparse.Namespace) -> list[str]:
    argv = ["--tenant", args.namespace]
    if args.output is not None:
        argv.extend(["--output", str(args.output)])
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args, remainder = parser.parse_known_args(argv)

    if args.command == "packet":
        return _run_packet(args)
    if args.command == "parity":
        return _run_parity(args)
    if args.command == "duplicates":
        from endorlabs.workflows.reports.analyze.duplicate_projects import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "cli-vs-cloud":
        from endorlabs.workflows.reports.analyze.cli_vs_cloud import main as run

        return run(_tenant_argv(args) + remainder)
    if args.command == "login-count":
        from endorlabs.workflows.reports.analyze.auth_login_count import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "credential-expiry":
        from endorlabs.workflows.reports.analyze.auth_credential_expiry import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "auth-policies":
        from endorlabs.workflows.reports.analyze.auth_policies_audit import (
            main as run,
        )

        return run(_tenant_hint_argv(args) + remainder)
    if args.command == "ci-endorctl":
        from endorlabs.workflows.reports.analyze.ci_endorctl_audit import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "findings-trend":
        from endorlabs.workflows.reports.export.canvas.findings_trend_report import (
            main as run,
        )

        ft_argv = [args.namespace]
        if args.output_dir is not None:
            ft_argv.extend(["--output-dir", str(args.output_dir)])
        if args.canvas_dir is not None:
            ft_argv.extend(["--canvas-dir", str(args.canvas_dir)])
        ft_argv.extend(["--interval", args.interval, "--lookback", str(args.lookback)])
        if args.analysis_only:
            ft_argv.append("--analysis-only")
        if args.skip_canvas:
            ft_argv.append("--skip-canvas")
        return run(ft_argv)
    if args.command == "prf-analysis":
        from endorlabs.workflows.reports.export.canvas.prf_report import main as run

        prf_argv = [args.namespace]
        if args.output_dir is not None:
            prf_argv.extend(["--output-dir", str(args.output_dir)])
        if args.canvas_dir is not None:
            prf_argv.extend(["--canvas-dir", str(args.canvas_dir)])
        if args.chrome is not None:
            prf_argv.extend(["--chrome", str(args.chrome)])
        if args.skip_canvas:
            prf_argv.append("--skip-canvas")
        if args.skip_pdf:
            prf_argv.append("--skip-pdf")
        if args.html_only:
            prf_argv.append("--html-only")
        if args.analysis_only:
            prf_argv.append("--analysis-only")
        return run(prf_argv)

    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
