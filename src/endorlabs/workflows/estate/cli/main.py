"""Unified estate workflow CLI."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import endorlabs
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
    workspace_date_suffix,
    workspace_dir_for,
)

LOGGER = logging.getLogger(__name__)


def _attach_workspace_log(workspace_root: Path, log_filename: str) -> Path:
    """Append INFO+ messages to ``logs/<log_filename>`` under the workspace."""
    ensure_workspace_layout(workspace_root)
    log_path = logs_dir(workspace_root) / log_filename
    handler = logging.FileHandler(log_path, encoding="utf-8", mode="a")
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
        return workspace_dir_for(
            ".endorlabs-context", args.namespace, date_suffix=date_suffix
        )
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
        help="Workspace directory (default: .endorlabs-context/workspace/<slug>-<YYYYMMDD>/)",
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
    client = endorlabs.Client(tenant=args.namespace)
    try:
        date_suffix = args.date if args.date else None
        result = collect_workspace(
            client,
            namespace=args.namespace,
            workspace=workspace_root,
            date_suffix=date_suffix,
            max_workers=args.max_workers,
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
    if args.only:
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
        )
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1
    for step, detail in result.steps.items():
        LOGGER.info("  %s: %s", step, detail)
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    workspace_root = _resolve_workspace(args)
    summary = summarize_workspace_dir(workspace_root)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        from endorlabs.workflows.estate.export.summarize import format_summary_text

        print(format_summary_text(summary))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="endor-estate",
        description="Estate workflows: pull data, analyze, summarize.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pull = sub.add_parser("pull", help="Collect estate resources into workspace")
    _add_common_args(pull)
    pull.add_argument("--max-workers", type=int, default=16)
    pull.add_argument("--max-pages", type=int, default=0)
    pull.add_argument("--page-size", type=int, default=500)
    pull.add_argument("--resume", action="store_true")
    pull.add_argument("--overwrite", action="store_true")
    pull.add_argument(
        "--preflight", action="store_true", help="Run list_resource_count per shard"
    )
    pull.add_argument("--validate-counts", action="store_true")
    pull.set_defaults(func=cmd_pull)

    analyze = sub.add_parser(
        "analyze", help="Run disk-first IR transforms and dashboard viz"
    )
    _add_common_args(analyze)
    analyze.add_argument(
        "--only",
        help="Comma-separated steps: cardinality,risk,graph,viz",
    )
    analyze.add_argument("--top-n", type=int, default=20)
    analyze.add_argument("--scorer", default="critical_high_count")
    analyze.add_argument("--skip-metrics", action="store_true")
    analyze.add_argument("--skip-validate", action="store_true")
    analyze.set_defaults(func=cmd_analyze)

    summarize = sub.add_parser("summarize", help="Summarize workspace IR")
    _add_common_args(summarize)
    summarize.add_argument("--json", action="store_true")
    summarize.set_defaults(func=cmd_summarize)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
