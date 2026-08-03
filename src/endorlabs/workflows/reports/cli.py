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
from endorlabs.workflows.reports.bundles.executive_packet import (
    build_report_packet,
    upsert_code_findings_burndown,
)
from endorlabs.workflows.reports.export.html.render import (
    default_packet_output_dir,
    default_patches_report_dir,
    render_report_packet,
)
from endorlabs.workflows.reports.parity import compare_packet_cube
from endorlabs.workflows.reports.schemas.packet_v0 import PATCHES_RUN_BUCKET, RUN_BUCKET


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
    packet.add_argument(
        "--skip-findings-burndown",
        action="store_true",
        help="Skip SCA (vulnerability) FindingLog burndown.",
    )
    packet.add_argument(
        "--skip-sca-burndown",
        action="store_true",
        help="Alias for --skip-findings-burndown.",
    )
    packet.add_argument(
        "--skip-code-findings-burndown",
        action="store_true",
        help="Skip SAST / AI-SAST / Secrets FindingLog burndown.",
    )
    packet.add_argument(
        "--skip-patches",
        action="store_true",
        help="Skip Endor Patches executive page (Finding list pull).",
    )
    packet.add_argument(
        "--patches-only",
        action="store_true",
        help=(
            "Build and render only the Endor Patches page (skip onboarding, "
            "sprawl, burndowns). Default output under "
            f".endorlabs-context/workspace/runs/{PATCHES_RUN_BUCKET}/"
            "<namespace>-MMDDYY/."
        ),
    )
    packet.add_argument(
        "--patches-date-suffix",
        default=None,
        help=(
            "Date suffix for --patches-only output dirs (default: today's "
            "MMDDYY). Example: 072926."
        ),
    )
    packet.add_argument("--timeout", type=float, default=900.0)
    return packet


def _upsert_code_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    upsert = sub.add_parser(
        "upsert-code-findings",
        help=(
            "Rebuild only SAST/AI-SAST/Secrets burndown into an existing packet "
            "directory (keeps onboarding, sprawl, SCA)."
        ),
    )
    upsert.add_argument(
        "--packet-dir",
        type=Path,
        required=True,
        help="Existing packet output dir containing data/packet.cube.json.",
    )
    upsert.add_argument("--lookback", type=int, default=None)
    upsert.add_argument("--min-projects", type=int, default=1)
    upsert.add_argument("--workers", type=int, default=24)
    upsert.add_argument("--timeout", type=float, default=900.0)
    return upsert


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
    parity.add_argument(
        "--skip-findings-burndown",
        action="store_true",
        help="Skip SCA (vulnerability) FindingLog burndown.",
    )
    parity.add_argument(
        "--skip-sca-burndown",
        action="store_true",
        help="Alias for --skip-findings-burndown.",
    )
    parity.add_argument(
        "--skip-code-findings-burndown",
        action="store_true",
        help="Skip SAST / AI-SAST / Secrets FindingLog burndown.",
    )
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
    _upsert_code_parser(sub)
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

    pkg = sub.add_parser(
        "package-resolution",
        help=(
            "Main-context PackageVersion resolution CSV + interactive HTML "
            "(unresolved/manifest, dependency resolution, reachability)."
        ),
    )
    _add_namespace(pkg)
    pkg.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path (default: workspace/runs/package-resolution/...).",
    )
    pkg.add_argument(
        "--html-dir",
        type=Path,
        default=None,
        help=(
            "HTML output directory "
            "(default: workspace/runs/package-resolution/<tenant>-html/)."
        ),
    )
    pkg.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Existing CSV for --html-only (skip live API collection).",
    )
    pkg.add_argument("--max-workers", type=int, default=16)
    pkg.add_argument("--max-inflight", type=int, default=64)
    pkg.add_argument(
        "--json-summary",
        type=Path,
        default=None,
        help="Optional JSON summary path written next to the CSV run.",
    )
    pkg.add_argument("--skip-html", action="store_true")
    pkg.add_argument(
        "--html-only",
        action="store_true",
        help="Render HTML from --csv (or --output) without calling the API.",
    )
    pkg.add_argument("--timeout", type=float, default=120.0)
    return parser


def _default_parity_dir(namespace: str) -> Path:
    slug = sanitize_path_segment(namespace)
    day = datetime.now(UTC).strftime("%Y%m%d")
    return default_runs_dir("report-parity") / f"{slug}-{day}"


def _run_upsert_code_findings(args: argparse.Namespace) -> int:
    packet_dir = Path(args.packet_dir)
    cube_path = packet_dir / "data" / "packet.cube.json"
    if not cube_path.is_file():
        print(f"Missing cube: {cube_path}", file=sys.stderr)
        return 2
    cube = json.loads(cube_path.read_text(encoding="utf-8"))
    tenant = str(cube.get("tenant") or "")
    if not tenant:
        print("Cube missing tenant", file=sys.stderr)
        return 2
    print(f"upsert code findings into {packet_dir} …", flush=True)
    client = endorlabs.Client(tenant=tenant, timeout=float(args.timeout))
    try:
        cube = upsert_code_findings_burndown(
            client,
            cube,
            lookback=args.lookback,
            min_projects=int(args.min_projects),
            max_workers=int(args.workers),
        )
    finally:
        client.close()
    print("rendering…", flush=True)
    written = render_report_packet(cube, packet_dir)
    code = (cube.get("reports") or {}).get("codeFindingsBurndown") or {}
    print(
        "code categories:",
        list((code.get("byCategory") or {}).keys()),
        flush=True,
    )
    for key, block in (code.get("byCategory") or {}).items():
        meta = block.get("tagSeriesMeta") or {}
        print(
            f"  {key}: ready={meta.get('seriesReadyCount')} "
            f"facets={block.get('facetKeys')}",
            flush=True,
        )
    print(f"Wrote {len(written)} files under {packet_dir}", flush=True)
    return 0


def _run_packet(args: argparse.Namespace) -> int:
    patches_only = bool(getattr(args, "patches_only", False))
    skip_patches = bool(getattr(args, "skip_patches", False))
    if patches_only and skip_patches:
        print("error: --patches-only conflicts with --skip-patches", file=sys.stderr)
        return 2

    if args.output_dir:
        out_dir = Path(args.output_dir)
    elif patches_only:
        suffix = getattr(args, "patches_date_suffix", None)
        out_dir = default_patches_report_dir(args.namespace, date_suffix=suffix)
    else:
        out_dir = default_packet_output_dir(args.namespace)

    client = endorlabs.Client(tenant=args.namespace, timeout=float(args.timeout))
    try:
        skip_sca = bool(
            getattr(args, "skip_findings_burndown", False)
            or getattr(args, "skip_sca_burndown", False)
        )
        if patches_only:
            cube = build_report_packet(
                client,
                args.namespace,
                lookback=int(args.lookback),
                min_projects=int(args.min_projects),
                max_workers=int(args.workers),
                patches_only=True,
                include_patches=True,
            )
        else:
            cube = build_report_packet(
                client,
                args.namespace,
                lookback=int(args.lookback),
                min_projects=int(args.min_projects),
                max_workers=int(args.workers),
                include_version_sprawl=not args.skip_version_sprawl,
                include_sca_burndown=not skip_sca,
                include_code_findings_burndown=not getattr(
                    args, "skip_code_findings_burndown", False
                ),
                include_patches=not skip_patches,
            )
    finally:
        client.close()
    written = render_report_packet(cube, out_dir, patches_only=patches_only)
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
        skip_sca = bool(
            getattr(args, "skip_findings_burndown", False)
            or getattr(args, "skip_sca_burndown", False)
        )
        cube = build_report_packet(
            client,
            args.namespace,
            lookback=int(args.lookback),
            min_projects=int(args.min_projects),
            max_workers=int(args.workers),
            include_version_sprawl=not args.skip_version_sprawl,
            include_sca_burndown=not skip_sca,
            include_code_findings_burndown=not getattr(
                args, "skip_code_findings_burndown", False
            ),
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
    if args.command == "upsert-code-findings":
        return _run_upsert_code_findings(args)
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
    if args.command == "package-resolution":
        return _run_package_resolution(args)

    parser.error(f"unknown command {args.command!r}")
    return 2


def _run_package_resolution(args: argparse.Namespace) -> int:
    from endorlabs.workflows.reports.analyze.package_resolution import (
        RUN_BUCKET,
    )
    from endorlabs.workflows.reports.analyze.package_resolution import (
        main as collect_main,
    )
    from endorlabs.workflows.reports.export.html.package_resolution import (
        main as html_main,
    )

    csv_path = args.csv or args.output
    if args.html_only:
        if csv_path is None:
            safe = sanitize_path_segment(args.namespace)
            csv_path = default_runs_dir(RUN_BUCKET) / f"{safe}-package-resolution.csv"
        if not Path(csv_path).is_file():
            print(f"CSV not found for --html-only: {csv_path}", file=sys.stderr)
            return 2
        html_argv = ["--csv", str(csv_path), "--tenant", args.namespace]
        if args.html_dir is not None:
            html_argv.extend(["--output-dir", str(args.html_dir)])
        return html_main(html_argv)

    collect_argv = [
        "--tenant",
        args.namespace,
        "--max-workers",
        str(args.max_workers),
        "--max-inflight",
        str(args.max_inflight),
        "--timeout",
        str(args.timeout),
    ]
    if args.output is not None:
        collect_argv.extend(["--output", str(args.output)])
    if args.json_summary is not None:
        collect_argv.extend(["--json-summary", str(args.json_summary)])
    rc = collect_main(collect_argv)
    if rc != 0:
        return rc

    if args.skip_html:
        return 0

    if args.output is not None:
        csv_path = args.output
    else:
        safe = sanitize_path_segment(args.namespace)
        csv_path = default_runs_dir(RUN_BUCKET) / f"{safe}-package-resolution.csv"
    html_argv = ["--csv", str(csv_path), "--tenant", args.namespace]
    if args.html_dir is not None:
        html_argv.extend(["--output-dir", str(args.html_dir)])
    return html_main(html_argv)


if __name__ == "__main__":
    sys.exit(main())
