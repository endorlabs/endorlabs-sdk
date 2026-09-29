"""``endor-license-export`` — scheduleable dependency + SPDX license export."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from endorlabs.context.paths import task_activity_dir
from endorlabs.workflows.common.cli_client import (
    add_client_auth_arguments,
    client_from_namespace_args,
)
from endorlabs.workflows.license_export.inventory import (
    collect_dependency_inventory,
    load_inventory_jsonl,
    unique_package_version_uuids,
)
from endorlabs.workflows.license_export.join import (
    default_join_filename,
    write_joined_export,
)
from endorlabs.workflows.license_export.pipeline import (
    default_output_dir,
    format_summary_line,
    namespace_work_dir,
    run_license_export,
)
from endorlabs.workflows.license_export.resolve import (
    LICENSE_CACHE_FILENAME,
    LICENSE_OBJECTS_FILENAME,
    resolve_licenses,
)
from endorlabs.workflows.license_export.summary import (
    ElapsedTimer,
    build_export_summary,
    summarize_license_cache,
    write_export_summary,
)


def _add_inventory_override_flags(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument(
        "--filter",
        default=None,
        dest="extra_filter",
        help=(
            "Extra MQL AND-ed with mandatory MAIN + importer project_uuid "
            "(inventory/run only). Cannot drop MAIN/importer safety."
        ),
    )
    _ = parser.add_argument(
        "--mask",
        default=None,
        help=(
            "Replace the default DependencyMetadata list mask. "
            "Omitting join fields yields empty CSV columns."
        ),
    )


def _add_license_object_flag(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument(
        "--include-license-object",
        action="store_true",
        help=(
            "Also write license_objects.jsonl (full PackageLicenseQuery body). "
            "With --format jsonl, embed license_object on each joined row."
        ),
    )


def _add_shared_flags(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument(
        "-n",
        "--namespace",
        action="append",
        dest="namespaces",
        default=None,
        help=(
            "Namespace to export (repeatable). Default: ENDOR_NAMESPACE. "
            "For multi-NS scheduled jobs, pass -n example-tenant multiple "
            "times or use --namespaces-file."
        ),
    )
    _ = parser.add_argument(
        "--namespaces-file",
        type=Path,
        default=None,
        help="File with one namespace path per line (# comments allowed).",
    )
    _ = parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory (default under "
            f"{task_activity_dir('<namespace>', 'licenses').as_posix()}/)."
        ),
    )
    _ = parser.add_argument(
        "--format",
        choices=["csv", "jsonl"],
        default="csv",
        help="Joined export format (default: csv).",
    )
    _ = parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume incomplete project shards (JSONL upsert by primary key).",
    )
    _ = parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reset inventory/checkpoint for namespaces in this run.",
    )
    _ = parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Parallel project / query workers (default: cpu count, 4-16).",
    )
    _ = parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max DM list pages per project (0 = unlimited).",
    )
    _ = parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="DM list page_size (default: 500; lower if shards 504).",
    )
    _ = parser.add_argument(
        "--license-cache",
        type=Path,
        default=None,
        help=(
            "Shared license cache JSONL path "
            "(default: <output-dir>/license_cache.jsonl)."
        ),
    )
    _ = parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help=(
            "BatchPackageLicenseQuery chunk size (default: 100). "
            "Chunks that 404 fall back to per-PV PackageLicenseQuery."
        ),
    )
    add_client_auth_arguments(parser)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export current-state dependency inventory with SPDX licenses "
            "(MAIN-context DependencyMetadata + PackageLicenseQuery). "
            "Designed for scheduled CI: one joined CSV/JSONL per namespace. "
            "Default subcommand is ``run`` when omitted. "
            "Auth: env or --token / --api-key+--api-secret (no browser; "
            "refresh first with endor-auth refresh)."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser(
        "run",
        help="inventory → resolve → join (default when no subcommand).",
    )
    _add_shared_flags(run_p)
    _add_inventory_override_flags(run_p)
    _add_license_object_flag(run_p)

    inv_p = sub.add_parser(
        "inventory",
        help="Phase 1: MAIN-context DependencyMetadata inventory only.",
    )
    _add_shared_flags(inv_p)
    _add_inventory_override_flags(inv_p)

    res_p = sub.add_parser(
        "resolve",
        help="Phase 2: resolve licenses for an existing inventory JSONL.",
    )
    _add_shared_flags(res_p)
    _add_license_object_flag(res_p)
    _ = res_p.add_argument(
        "--inventory",
        type=Path,
        default=None,
        help="Path to dependency_inventory.jsonl (default: under namespace work dir).",
    )

    join_p = sub.add_parser(
        "join",
        help="Phase 3: join inventory + license cache into CSV/JSONL.",
    )
    _add_shared_flags(join_p)
    _add_license_object_flag(join_p)
    _ = join_p.add_argument(
        "--inventory",
        type=Path,
        default=None,
        help="Path to dependency_inventory.jsonl.",
    )
    return parser


_SUBCOMMANDS = frozenset({"run", "inventory", "resolve", "join"})


def _read_namespaces_file(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        lines.append(text)
    return lines


def _resolve_namespaces(args: argparse.Namespace) -> list[str]:
    found: list[str] = []
    if args.namespaces:
        found.extend(str(n).strip() for n in args.namespaces if str(n).strip())
    if getattr(args, "namespaces_file", None):
        found.extend(_read_namespaces_file(Path(args.namespaces_file)))
    if not found:
        env = os.getenv("ENDOR_NAMESPACE")
        if env and env.strip():
            found.append(env.strip())
    # Dedupe preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for ns in found:
        if ns not in seen:
            seen.add(ns)
            out.append(ns)
    if not out:
        raise SystemExit(
            "Namespace required: pass -n/--namespace, --namespaces-file, "
            "or set ENDOR_NAMESPACE."
        )
    return out


def _print_result_errors(errors: list[str]) -> None:
    for err in errors:
        print(err, file=sys.stderr)


def _cmd_run(client: Any, args: argparse.Namespace) -> int:
    result = run_license_export(
        client,
        namespaces=_resolve_namespaces(args),
        output_dir=args.output_dir,
        export_format=args.format,
        max_workers=args.max_workers,
        max_pages=args.max_pages,
        page_size=args.page_size,
        resume=args.resume,
        overwrite=args.overwrite,
        license_cache=args.license_cache,
        batch_size=args.batch_size,
        extra_filter=getattr(args, "extra_filter", None),
        mask=getattr(args, "mask", None),
        include_license_object=bool(getattr(args, "include_license_object", False)),
    )
    print(result.message)
    for ns_result in result.namespace_results:
        print(f"  [{ns_result.status}] {ns_result.namespace}: {ns_result.join_path}")
    if result.summary:
        print(format_summary_line(result.summary))
        print(f"  → {result.summary_path}")
    if result.status in {"error", "partial"}:
        _print_result_errors(result.errors)
        return 1 if result.status == "error" else 0
    return 0


def _cmd_inventory(client: Any, args: argparse.Namespace) -> int:
    namespaces = _resolve_namespaces(args)
    base = (
        Path(args.output_dir)
        if args.output_dir is not None
        else default_output_dir(namespaces[0])
    )
    exit_code = 0
    timer = ElapsedTimer()
    inv_rows = 0
    projects_total = 0
    complete = 0
    failed = 0
    for ns in namespaces:
        work = namespace_work_dir(base, ns)
        result = collect_dependency_inventory(
            client,
            namespace=ns,
            output_dir=work,
            max_workers=args.max_workers,
            max_pages=args.max_pages,
            page_size=args.page_size,
            resume=args.resume,
            overwrite=args.overwrite,
            extra_filter=getattr(args, "extra_filter", None),
            mask=getattr(args, "mask", None),
        )
        print(result.message)
        print(f"  → {result.inventory_path}")
        inv_rows += result.row_count
        projects_total += result.project_count
        complete += result.complete_shards
        failed += result.failed_shards
        if result.status == "error":
            _print_result_errors(result.errors)
            exit_code = 1
        elif result.status == "partial":
            _print_result_errors(result.errors)
    summary = build_export_summary(
        namespaces=namespaces,
        output_dir=base,
        workers=args.max_workers,
        elapsed_seconds=timer.elapsed(),
        projects_total=projects_total,
        projects_complete=complete,
        projects_failed=failed,
        inventory_rows=inv_rows,
        status="error" if exit_code else "success",
        message="inventory phase complete",
    )
    path = write_export_summary(base, summary)
    print(format_summary_line(summary))
    print(f"  → {path}")
    return exit_code


def _cmd_resolve(client: Any, args: argparse.Namespace) -> int:
    namespaces = _resolve_namespaces(args)
    base = (
        Path(args.output_dir)
        if args.output_dir is not None
        else default_output_dir(namespaces[0])
    )
    cache_path = (
        Path(args.license_cache)
        if args.license_cache is not None
        else base / LICENSE_CACHE_FILENAME
    )
    objects_path = base / LICENSE_OBJECTS_FILENAME
    include_obj = bool(getattr(args, "include_license_object", False))
    exit_code = 0
    for ns in namespaces:
        work = namespace_work_dir(base, ns)
        inv_path = (
            Path(args.inventory)
            if args.inventory is not None
            else work / "dependency_inventory.jsonl"
        )
        rows = load_inventory_jsonl(inv_path)
        pvs = unique_package_version_uuids(rows)
        result = resolve_licenses(
            client,
            namespace=ns,
            package_version_uuids=pvs,
            cache_path=cache_path,
            batch_size=args.batch_size,
            max_workers=args.max_workers,
            overwrite=args.overwrite and ns == namespaces[0],
            include_license_object=include_obj,
            objects_path=objects_path,
        )
        print(result.message)
        print(f"  → {result.cache_path}")
        if include_obj and result.objects_path:
            print(f"  → {result.objects_path}")
        if result.status == "error":
            _print_result_errors(result.errors)
            exit_code = 1
        elif result.status == "partial":
            _print_result_errors(result.errors)
    stats = summarize_license_cache(cache_path)
    summary = build_export_summary(
        namespaces=namespaces,
        output_dir=base,
        license_consensus=stats["consensus"],
        license_query=stats["query"],
        license_missing=stats["missing"],
        license_with_primary_spdx=stats["with_primary_spdx"],
        license_cache_path=str(cache_path),
        license_objects_path=str(objects_path) if include_obj else "",
        unique_pvs=stats["consensus"] + stats["query"] + stats["missing"],
        status="error" if exit_code else "success",
        message="resolve phase complete",
    )
    path = write_export_summary(base, summary)
    print(format_summary_line(summary))
    print(f"  → {path}")
    return exit_code


def _cmd_join(client: Any, args: argparse.Namespace) -> int:
    del client  # join is disk-only
    namespaces = _resolve_namespaces(args)
    base = (
        Path(args.output_dir)
        if args.output_dir is not None
        else default_output_dir(namespaces[0])
    )
    cache_path = (
        Path(args.license_cache)
        if args.license_cache is not None
        else base / LICENSE_CACHE_FILENAME
    )
    objects_path = base / LICENSE_OBJECTS_FILENAME
    include_obj = bool(getattr(args, "include_license_object", False))
    join_rows = 0
    join_paths: list[str] = []
    for ns in namespaces:
        work = namespace_work_dir(base, ns)
        inv_path = (
            Path(args.inventory)
            if args.inventory is not None
            else work / "dependency_inventory.jsonl"
        )
        out = work / default_join_filename(ns, args.format)
        result = write_joined_export(
            inventory_path=inv_path,
            cache_path=cache_path,
            output_path=out,
            export_format=args.format,
            objects_path=objects_path if include_obj else None,
            include_license_object=include_obj,
        )
        print(result.message)
        join_rows += result.row_count
        join_paths.append(str(out))
    summary = build_export_summary(
        namespaces=namespaces,
        output_dir=base,
        export_format=args.format,
        join_rows=join_rows,
        join_paths=join_paths,
        license_cache_path=str(cache_path),
        license_objects_path=str(objects_path) if include_obj else "",
        status="success",
        message="join phase complete",
    )
    path = write_export_summary(base, summary)
    print(format_summary_line(summary))
    print(f"  → {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``endor-license-export``."""
    raw = list(argv) if argv is not None else sys.argv[1:]
    if not raw or (raw[0] not in _SUBCOMMANDS and raw[0] not in {"-h", "--help"}):
        raw = ["run", *raw]

    parser = _build_parser()
    args = parser.parse_args(raw)
    command = args.command or "run"

    try:
        namespaces = _resolve_namespaces(args)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    client = client_from_namespace_args(namespaces[0], args)
    try:
        if command == "inventory":
            return _cmd_inventory(client, args)
        if command == "resolve":
            return _cmd_resolve(client, args)
        if command == "join":
            return _cmd_join(client, args)
        return _cmd_run(client, args)
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
