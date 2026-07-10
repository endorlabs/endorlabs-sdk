"""Unified estate workflow CLI."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import endorlabs
from endorlabs.context.paths import (
    DEFAULT_CONTEXT_DIR,
    workspace_date_suffix,
    workspace_dir_for,
)
from endorlabs.tools.list_bounds import resolve_collect_max_workers
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.workspace import analyze_workspace
from endorlabs.workflows.estate.collect.runner import collect_workspace
from endorlabs.workflows.estate.contracts.resources import (
    ANALYZE_LOG_FILENAME,
    PULL_LOG_FILENAME,
)
from endorlabs.workflows.estate.export.summarize import summarize_workspace_dir
from endorlabs.workflows.estate.workspace.paths import (
    ensure_workspace_layout,
    logs_dir,
    resolve_workspace_root,
)

LOGGER = get_resource_logger(__name__)


def _attach_workspace_log(workspace_root: Path, log_filename: str) -> Path:
    """Append INFO+ messages to ``logs/<log_filename>`` under the workspace."""
    ensure_workspace_layout(workspace_root)
    log_path = logs_dir(workspace_root) / log_filename
    handler = logging.FileHandler(log_path, encoding="utf-8", mode="a")
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    LOGGER.info("Workspace log: %s", log_path)
    return log_path


def _resolve_workspace(args: argparse.Namespace) -> Path:
    if args.workspace:
        return resolve_workspace_root(Path(args.workspace))
    if args.namespace:
        date_suffix = (
            args.date if getattr(args, "date", None) else workspace_date_suffix()
        )
        return workspace_dir_for(args.namespace, date_suffix=date_suffix)
    raise ValueError("Provide --workspace or --namespace")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--namespace",
        "-n",
        default=os.environ.get("ENDOR_NAMESPACE"),
        help="Estate root namespace",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        help=(
            f"Workspace directory (default: {DEFAULT_CONTEXT_DIR}/workspace/"
            "<slug>-<YYYYMMDD>/)"
        ),
    )
    parser.add_argument(
        "--date",
        help="UTC YYYYMMDD suffix for default workspace path (default: today)",
    )


def cmd_pull(args: argparse.Namespace) -> int:
    if not args.namespace:
        LOGGER.error("Provide --namespace or set ENDOR_NAMESPACE")
        return 2
    workspace_root = _resolve_workspace(args)
    _attach_workspace_log(workspace_root, PULL_LOG_FILENAME)
    max_workers = resolve_collect_max_workers(args.max_workers)
    LOGGER.info("Pull max_workers=%s", max_workers)
    client = endorlabs.Client(tenant=args.namespace)
    try:
        date_suffix = args.date or None
        result = collect_workspace(
            client,
            namespace=args.namespace,
            workspace=workspace_root,
            date_suffix=date_suffix,
            max_workers=max_workers,
            max_pages=args.max_pages,
            page_size=args.page_size,
            resume=args.resume,
            overwrite=args.overwrite,
            preflight=args.preflight,
            validate_counts=args.validate_counts,
        )
    finally:
        client.close()
    LOGGER.info("Workspace: %s", result.workspace_root)
    for resource_id, detail in result.resources.items():
        LOGGER.info("  %s: %s", resource_id, detail)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    if not args.namespace and not args.workspace:
        LOGGER.error("Provide --namespace or --workspace")
        return 2
    workspace_root = _resolve_workspace(args)
    _attach_workspace_log(workspace_root, ANALYZE_LOG_FILENAME)
    namespace = args.namespace or workspace_root.name.split("-")[0].replace("_", ".")
    only = None
    if args.only_relationships:
        if args.only:
            LOGGER.error("Use --only-relationships or --only, not both")
            return 2
        only = ("relationships",)
    elif args.only:
        only = tuple(part.strip() for part in args.only.split(",") if part.strip())
    try:
        result = analyze_workspace(
            workspace_root,
            namespace=namespace,
            only=only,
            top_n=args.top_n,
            scorer=args.scorer,
            skip_metrics=args.skip_metrics,
            skip_validate=args.skip_validate,
            relationship_max_depth=args.relationship_max_depth,
            relationship_max_workers=args.relationship_max_workers,
            focus_producer_project_uuid=(
                (args.focus_producer_project_uuid or "").strip() or None
            ),
        )
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1
    for step, detail in result.steps.items():
        LOGGER.info("  %s: %s", step, detail)
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    workspace_root = _resolve_workspace(args)
    try:
        summary = summarize_workspace_dir(
            workspace_root,
            namespace=args.namespace,
        )
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        from endorlabs.workflows.estate.export.summarize import format_summary_text

        print(format_summary_text(summary))
    return 0


def cmd_export_version(args: argparse.Namespace) -> int:
    from endorlabs.workflows.estate.analyze.cardinality.export import (
        main as export_main,
    )

    argv: list[str] = []
    if args.namespace:
        argv.extend(["--namespace", args.namespace])
    if args.output:
        argv.extend(["--output", args.output])
    if args.usage_detail_output:
        argv.extend(["--usage-detail-output", args.usage_detail_output])
    if args.max_pages is not None:
        argv.extend(["--max-pages", str(args.max_pages)])
    if args.page_size is not None:
        argv.extend(["--page-size", str(args.page_size)])
    if args.progress_batch is not None:
        argv.extend(["--progress-batch", str(args.progress_batch)])
    if args.max_project_workers is not None:
        argv.extend(["--max-project-workers", str(args.max_project_workers)])
    if args.request_timeout is not None:
        argv.extend(["--request-timeout", str(args.request_timeout)])
    if args.package_name_match:
        argv.extend(["--package-name-match", args.package_name_match])
    if args.exact_package_name:
        argv.extend(["--exact-package-name", args.exact_package_name])
    if args.remediation_cve:
        argv.extend(["--remediation-cve", args.remediation_cve])
    if args.remediation_output:
        argv.extend(["--remediation-output", args.remediation_output])
    return export_main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="endor-estate",
        description="Estate workflows: pull data, analyze, summarize, export-version.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pull = sub.add_parser("pull", help="Collect estate resources into workspace")
    _add_common_args(pull)
    pull.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Parallel shard workers (default: os.cpu_count(), min 4, max 16)",
    )
    pull.add_argument("--max-pages", type=int, default=0)
    pull.add_argument("--page-size", type=int, default=500)
    pull.add_argument("--resume", action="store_true")
    pull.add_argument("--overwrite", action="store_true")
    pull.add_argument(
        "--preflight", action="store_true", help="Run count_for_progress per shard"
    )
    pull.add_argument("--validate-counts", action="store_true")
    pull.set_defaults(func=cmd_pull)

    analyze = sub.add_parser(
        "analyze", help="Run disk-first IR transforms and dashboard viz"
    )
    _add_common_args(analyze)
    analyze.add_argument(
        "--only",
        help="Comma-separated steps: cardinality,risk,graph,viz,relationships",
    )
    analyze.add_argument(
        "--only-relationships",
        action="store_true",
        help=(
            "Live API project relationship map into workspace "
            "intermediate-representation/ (alias for --only relationships)."
        ),
    )
    analyze.add_argument("--top-n", type=int, default=20)
    analyze.add_argument("--scorer", default="critical_high_count")
    analyze.add_argument("--skip-metrics", action="store_true")
    analyze.add_argument("--skip-validate", action="store_true")
    analyze.add_argument(
        "--relationship-max-depth",
        type=int,
        default=3,
        help="Max hop count when --only relationships is used. Default: 3",
    )
    analyze.add_argument(
        "--relationship-max-workers",
        type=int,
        default=16,
        help="Parallel DM workers for relationship map. Default: 16",
    )
    analyze.add_argument(
        "--focus-producer-project-uuid",
        default="",
        help=(
            "With --only relationships: restrict to consumer→producer edges where "
            "this project UUID is the producer (breaking-change consumer discovery)."
        ),
    )
    analyze.set_defaults(func=cmd_analyze)

    summarize = sub.add_parser("summarize", help="Summarize workspace IR")
    _add_common_args(summarize)
    summarize.add_argument("--json", action="store_true")
    summarize.set_defaults(func=cmd_summarize)

    export_version = sub.add_parser(
        "export-version",
        help="Live API version-cardinality export (grouped DependencyMetadata)",
    )
    export_version.add_argument(
        "--namespace",
        "-n",
        default=os.environ.get("ENDOR_NAMESPACE"),
        help="Estate root namespace",
    )
    export_version.add_argument("--output", "-o", help="Output CSV path")
    export_version.add_argument("--usage-detail-output")
    export_version.add_argument("--max-pages", type=int, default=None)
    export_version.add_argument("--page-size", type=int, default=None)
    export_version.add_argument("--progress-batch", type=int, default=None)
    export_version.add_argument("--max-project-workers", type=int, default=None)
    export_version.add_argument("--request-timeout", type=float, default=None)
    export_version.add_argument("--package-name-match")
    export_version.add_argument("--exact-package-name")
    export_version.add_argument("--remediation-cve")
    export_version.add_argument("--remediation-output")
    export_version.set_defaults(func=cmd_export_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
