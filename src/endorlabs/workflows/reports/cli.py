"""Unified CLI for tenant and namespace report workflows."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path

import endorlabs
from endorlabs.context.paths import (
    default_reports_subdir,
    flat_task_dir,
    reports_dir,
    tenant_day_slug,
)
from endorlabs.workflows.reports.bundles.executive_packet import (
    build_report_packet,
    upsert_code_findings_burndown,
)
from endorlabs.workflows.reports.catalog import (
    REPORT_CATALOG,
    catalog_epilog,
    catalog_for_list,
)
from endorlabs.workflows.reports.export.html.render import (
    default_packet_output_dir,
    default_patches_report_dir,
    render_report_packet,
)
from endorlabs.workflows.reports.logging import (
    configure_reports_cli_logging,
    milestone,
    resolve_log_level,
)
from endorlabs.workflows.reports.parity import compare_packet_cube

_NAMESPACE_HELP = (
    "Namespace scope for API lists and output paths (tenant root or child "
    "segment, e.g. example-tenant or example-tenant.child). "
    "Falls back to ENDOR_NAMESPACE."
)


def _namespace_parent() -> argparse.ArgumentParser:
    """Shared ``-n`` / ``--namespace`` for root and subcommands."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "-n",
        "--namespace",
        default=None,
        help=_NAMESPACE_HELP,
    )
    return parent


def _resolve_namespace(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    *,
    required: bool = True,
) -> str:
    """Merge explicit ``-n``, subcommand ``-n``, and ``ENDOR_NAMESPACE``."""
    ns = (getattr(args, "namespace", None) or "").strip()
    if not ns:
        ns = (os.environ.get("ENDOR_NAMESPACE") or "").strip()
    if required and not ns:
        parser.error("Namespace required: pass -n/--namespace or set ENDOR_NAMESPACE.")
    return ns


def _catalog_description(subcommand: str) -> str:
    for entry in REPORT_CATALOG:
        if entry.subcommand == subcommand:
            return f"{entry.summary} Default output: {entry.default_output}"
    return ""


def _warn_deprecated(command: str, replacement: str) -> None:
    warnings.warn(
        f"endor-reports {command} is deprecated; use {replacement} instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def _add_build_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lookback", type=int, default=13)
    parser.add_argument(
        "--min-projects",
        type=int,
        default=1,
        help=(
            "Display filter: omit tag series with fewer than this many tagged "
            "projects (default: 1 = all tags with series)."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=24,
        help="Parallel FindingLog matrix pulls for tagged projects (default: 24).",
    )
    parser.add_argument("--skip-version-sprawl", action="store_true")
    parser.add_argument(
        "--skip-findings-burndown",
        action="store_true",
        help="Skip SCA (vulnerability) FindingLog burndown.",
    )
    parser.add_argument(
        "--skip-sca-burndown",
        action="store_true",
        help="Alias for --skip-findings-burndown.",
    )
    parser.add_argument(
        "--skip-code-findings-burndown",
        action="store_true",
        help="Skip SAST / AI-SAST / Secrets FindingLog burndown.",
    )
    parser.add_argument(
        "--patches",
        action="store_true",
        help=(
            "Include the Endor Patches executive page (Finding list pull). "
            "Opt-in; omitted by default."
        ),
    )
    parser.add_argument(
        "--skip-patches",
        action="store_true",
        help=(
            "Deprecated no-op: patches are opt-in (use --patches to enable). "
            "Errors if combined with --patches."
        ),
    )
    parser.add_argument(
        "--patches-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Output directory for HTML + cube "
            f"(default: {reports_dir().as_posix()}/<slug>-<YYYY-MM-DD>/; "
            f"patches-only: {reports_dir().as_posix()}/patches/<slug>-<YYYY-MM-DD>/)."
        ),
    )
    parser.add_argument(
        "--date-suffix",
        default=None,
        help=(
            "UTC date suffix YYYY-MM-DD for default output dirs "
            "(default: today). Example: 2026-08-28."
        ),
    )
    parser.add_argument(
        "--patches-date-suffix",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=(
            "Progress log level on stdout (default: ENDOR_LOG_LEVEL or INFO). "
            "Stage milestones use the endorlabs.workflows.reports logger "
            "(RedactingFilter)."
        ),
    )


def _packet_parser(
    sub: argparse._SubParsersAction,
    *,
    ns_parent: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    packet = sub.add_parser(
        "packet",
        parents=[ns_parent],
        help="(deprecated) Build and render the executive HTML report packet.",
        description=_catalog_description("packet"),
    )
    _add_build_flags(packet)
    return packet


def _build_parser_sub(
    sub: argparse._SubParsersAction,
    *,
    ns_parent: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    build = sub.add_parser(
        "build",
        parents=[ns_parent],
        help="Build and render the executive HTML report packet.",
        description=_catalog_description("build"),
    )
    _add_build_flags(build)
    return build


def _patches_parser(
    sub: argparse._SubParsersAction,
    *,
    ns_parent: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    patches = sub.add_parser(
        "patches",
        parents=[ns_parent],
        help="Build and render only the Endor Patches executive page.",
        description=_catalog_description("patches"),
    )
    _add_build_flags(patches)
    patches.set_defaults(patches_only=True)
    return patches


def _list_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    list_cmd = sub.add_parser(
        "list",
        help="List report subcommands, categories, and default output paths.",
    )
    list_cmd.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    list_cmd.add_argument(
        "--include-deprecated",
        action="store_true",
        help="Include deprecated subcommands (packet, upsert-code-findings).",
    )
    return list_cmd


def _run_list(args: argparse.Namespace) -> int:
    rows = catalog_for_list(include_deprecated=bool(args.include_deprecated))
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    current = ""
    for row in rows:
        cat = row["category"]
        if cat != current:
            current = cat
            print(f"\n{cat}:")
        subcmd = row["subcommand"] or "(default build)"
        print(f"  {subcmd:22} {row['summary']}")
        print(f"    -> {row['default_output']}")
    print()
    return 0


def _refresh_code_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    refresh = sub.add_parser(
        "refresh-code",
        help=(
            "Rebuild only SAST/AI-SAST/Secrets burndown into an existing packet "
            "directory (keeps onboarding, sprawl, SCA)."
        ),
    )
    refresh.add_argument(
        "--packet-dir",
        type=Path,
        required=True,
        help="Existing packet output dir containing data/packet.cube.json.",
    )
    refresh.add_argument("--lookback", type=int, default=None)
    refresh.add_argument("--min-projects", type=int, default=1)
    refresh.add_argument("--workers", type=int, default=24)
    refresh.add_argument("--timeout", type=float, default=900.0)
    refresh.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=("Progress log level on stdout (default: ENDOR_LOG_LEVEL or INFO)."),
    )
    return refresh


def _upsert_code_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    upsert = sub.add_parser(
        "upsert-code-findings",
        help="(deprecated) Use refresh-code instead.",
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
    upsert.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=("Progress log level on stdout (default: ENDOR_LOG_LEVEL or INFO)."),
    )
    return upsert


def _parity_parser(
    sub: argparse._SubParsersAction,
    *,
    ns_parent: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parity = sub.add_parser(
        "parity",
        parents=[ns_parent],
        help="Build packet and compare metrics to scratch baseline JSON files.",
        description=_catalog_description("parity"),
    )
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
            f"(default: {flat_task_dir('parity').as_posix()}/<slug>-<YYYY-MM-DD>/)."
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
    *,
    ns_parent: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = sub.add_parser(
        name,
        parents=[ns_parent],
        help=help_text,
        description=_catalog_description(name) or help_text,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"CSV output path (default: {default_reports_subdir(name).as_posix()}/).",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser


def build_parser() -> argparse.ArgumentParser:
    ns_parent = _namespace_parent()
    parser = argparse.ArgumentParser(
        prog="endor-reports",
        parents=[ns_parent],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Endor Labs tenant and namespace report workflows. "
            "Default (no subcommand): build executive HTML packet with -n. "
            "Use `list` to see all report subcommands."
        ),
        epilog=catalog_epilog(),
    )
    _add_build_flags(parser)

    sub = parser.add_subparsers(dest="command", required=False)
    _list_parser(sub)
    _build_parser_sub(sub, ns_parent=ns_parent)
    _patches_parser(sub, ns_parent=ns_parent)
    _packet_parser(sub, ns_parent=ns_parent)
    _refresh_code_parser(sub)
    _upsert_code_parser(sub)
    _parity_parser(sub, ns_parent=ns_parent)
    _tenant_report_parser(
        sub,
        "duplicates",
        "Find duplicate project registrations.",
        ns_parent=ns_parent,
    )
    _tenant_report_parser(
        sub,
        "cli-vs-cloud",
        "Classify CLI vs cloud project registrations.",
        ns_parent=ns_parent,
    )
    _tenant_report_parser(
        sub,
        "login-count",
        "AuthenticationLog login counts by identity.",
        ns_parent=ns_parent,
    )
    _tenant_report_parser(
        sub,
        "credential-expiry",
        "Credential expiry horizon report.",
        ns_parent=ns_parent,
    )
    _tenant_report_parser(
        sub,
        "auth-policies",
        "Audit AuthorizationPolicy claim forms.",
        ns_parent=ns_parent,
    )
    _tenant_report_parser(
        sub,
        "ci-endorctl",
        "Audit CI endorctl versions from scan metadata.",
        ns_parent=ns_parent,
    )

    findings = sub.add_parser(
        "findings-trend",
        parents=[ns_parent],
        help="FindingLog weekly new-vs-resolved chart (JSON + optional canvas).",
        description=_catalog_description("findings-trend"),
    )
    findings.add_argument("--output-dir", type=Path, default=None)
    findings.add_argument("--canvas-dir", type=Path, default=None)
    findings.add_argument("--interval", default="week")
    findings.add_argument("--lookback", type=int, default=13)
    findings.add_argument("--analysis-only", action="store_true")
    findings.add_argument("--skip-canvas", action="store_true")

    prf = sub.add_parser(
        "prf-analysis",
        parents=[ns_parent],
        help="Potentially reachable findings analysis (JSON + canvas + PDF).",
        description=_catalog_description("prf-analysis"),
    )
    prf.add_argument("--output-dir", type=Path, default=None)
    prf.add_argument("--canvas-dir", type=Path, default=None)
    prf.add_argument("--chrome", type=Path, default=None)
    prf.add_argument("--skip-canvas", action="store_true")
    prf.add_argument("--skip-pdf", action="store_true")
    prf.add_argument("--html-only", action="store_true")
    prf.add_argument("--analysis-only", action="store_true")

    pkg = sub.add_parser(
        "package-resolution",
        parents=[ns_parent],
        help=(
            "Main-context PackageVersion resolution CSV + interactive HTML "
            "(unresolved/manifest, dependency resolution, reachability)."
        ),
        description=_catalog_description("package-resolution"),
    )
    pkg.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "CSV output path "
            f"(default: {default_reports_subdir('package-resolution').as_posix()}/)."
        ),
    )
    pkg.add_argument(
        "--html-dir",
        type=Path,
        default=None,
        help=(
            "HTML output directory "
            f"(default: {default_reports_subdir('package-resolution').as_posix()}/"
            "<tenant>/)."
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
    return flat_task_dir("parity") / tenant_day_slug(namespace)


def _run_refresh_code(args: argparse.Namespace) -> int:
    configure_reports_cli_logging(level=getattr(args, "log_level", None))
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
    milestone("packet", "cli.upsert_start")
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
    milestone("packet", "cli.render.start", mode="upsert_code")
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
    milestone("packet", "cli.upsert_done", files=len(written))
    return 0


def _run_packet(args: argparse.Namespace) -> int:
    configure_reports_cli_logging(level=getattr(args, "log_level", None))
    patches_only = bool(getattr(args, "patches_only", False))
    include_patches = bool(getattr(args, "patches", False))
    skip_patches = bool(getattr(args, "skip_patches", False))
    if patches_only and skip_patches:
        print("error: --patches-only conflicts with --skip-patches", file=sys.stderr)
        return 2
    if include_patches and skip_patches:
        print("error: --patches conflicts with --skip-patches", file=sys.stderr)
        return 2
    if skip_patches:
        print(
            "warning: --skip-patches is a no-op; Endor Patches is opt-in "
            "(pass --patches to include).",
            file=sys.stderr,
        )

    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        suffix = getattr(args, "date_suffix", None) or getattr(
            args, "patches_date_suffix", None
        )
        if patches_only:
            out_dir = default_patches_report_dir(args.namespace, date_suffix=suffix)
        else:
            out_dir = default_packet_output_dir(args.namespace, date_suffix=suffix)

    milestone(
        "packet",
        "cli.start",
        log_level=logging.getLevelName(
            resolve_log_level(getattr(args, "log_level", None))
        ),
        patches_only=int(patches_only),
        patches=int(include_patches or patches_only),
    )
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
                include_patches=include_patches,
            )
    finally:
        client.close()
    milestone("packet", "cli.render.start")
    written = render_report_packet(cube, out_dir, patches_only=patches_only)
    print(f"Wrote report packet to {out_dir}")
    for path in written:
        rel = path.name if path.parent == out_dir else path.relative_to(out_dir)
        print(f"  {rel}")
    gaps = [str(g) for g in (cube.get("dataGaps") or [])]
    if gaps:
        print(
            "warning: packet data gaps: " + ", ".join(gaps),
            file=sys.stderr,
            flush=True,
        )
        for key in gaps:
            meta = (cube.get("reportsMeta") or {}).get(key) or {}
            err = meta.get("error_type")
            if err:
                print(f"  {key}: {err}", file=sys.stderr, flush=True)
        milestone("packet", "cli.done", files=len(written), data_gaps=len(gaps))
        return 1
    milestone("packet", "cli.done", files=len(written))
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
    argv_list = sys.argv[1:] if argv is None else list(argv)
    ns_peek = argparse.ArgumentParser(add_help=False)
    ns_peek.add_argument("-n", "--namespace", default=None)
    ns_from_anywhere, _ = ns_peek.parse_known_args(argv_list)

    parser = build_parser()
    args, remainder = parser.parse_known_args(argv_list)

    if (ns_from_anywhere.namespace or "").strip():
        args.namespace = ns_from_anywhere.namespace

    command = args.command
    if command == "list":
        return _run_list(args)
    if command in (None, "build"):
        args.namespace = _resolve_namespace(args, parser)
        return _run_packet(args)
    if command == "patches":
        args.namespace = _resolve_namespace(args, parser)
        return _run_packet(args)
    if command == "packet":
        _warn_deprecated("packet", "endor-reports -n <tenant> (default build)")
        args.namespace = _resolve_namespace(args, parser)
        return _run_packet(args)
    if command == "refresh-code":
        return _run_refresh_code(args)
    if command == "upsert-code-findings":
        _warn_deprecated("upsert-code-findings", "refresh-code")
        return _run_refresh_code(args)
    if command == "parity":
        args.namespace = _resolve_namespace(args, parser)
        return _run_parity(args)
    if args.command == "duplicates":
        args.namespace = _resolve_namespace(args, parser)
        from endorlabs.workflows.reports.analyze.duplicate_projects import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "cli-vs-cloud":
        args.namespace = _resolve_namespace(args, parser)
        from endorlabs.workflows.reports.analyze.cli_vs_cloud import main as run

        return run(_tenant_argv(args) + remainder)
    if args.command == "login-count":
        args.namespace = _resolve_namespace(args, parser)
        from endorlabs.workflows.reports.analyze.auth_login_count import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "credential-expiry":
        args.namespace = _resolve_namespace(args, parser)
        from endorlabs.workflows.reports.analyze.auth_credential_expiry import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "auth-policies":
        args.namespace = _resolve_namespace(args, parser)
        from endorlabs.workflows.reports.analyze.auth_policies_audit import (
            main as run,
        )

        return run(_tenant_hint_argv(args) + remainder)
    if args.command == "ci-endorctl":
        args.namespace = _resolve_namespace(args, parser)
        from endorlabs.workflows.reports.analyze.ci_endorctl_audit import (
            main as run,
        )

        return run(_tenant_argv(args) + remainder)
    if args.command == "findings-trend":
        args.namespace = _resolve_namespace(args, parser)
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
        args.namespace = _resolve_namespace(args, parser)
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
        args.namespace = _resolve_namespace(args, parser)
        return _run_package_resolution(args)

    parser.error(f"unknown command {args.command!r}")
    return 2


def _run_package_resolution(args: argparse.Namespace) -> int:
    from endorlabs.workflows.reports.analyze.package_resolution import (
        default_package_resolution_csv_path,
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
            csv_path = default_package_resolution_csv_path(args.namespace)
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
        csv_path = default_package_resolution_csv_path(args.namespace)
    html_argv = ["--csv", str(csv_path), "--tenant", args.namespace]
    if args.html_dir is not None:
        html_argv.extend(["--output-dir", str(args.html_dir)])
    return html_main(html_argv)


if __name__ == "__main__":
    sys.exit(main())
