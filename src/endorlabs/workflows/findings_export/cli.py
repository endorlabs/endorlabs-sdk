"""CLI for ``endor-findings-export`` (MAIN Finding JSONL inventory)."""

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
from endorlabs.workflows.findings_export.pipeline import (
    run_findings_export,
)
from endorlabs.workflows.findings_export.summary import format_summary_line


def _add_flags(parser: argparse.ArgumentParser) -> None:
    _ = parser.add_argument(
        "-n",
        "--namespace",
        dest="namespaces",
        action="append",
        default=[],
        help=(
            "Namespace to export (repeatable). Also accepts ENDOR_NAMESPACE when unset."
        ),
    )
    _ = parser.add_argument(
        "--namespaces-file",
        type=Path,
        default=None,
        help="Text file with one namespace per line (# comments allowed).",
    )
    _ = parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Output directory (default under "
            f"{task_activity_dir('<namespace>', 'findings').as_posix()}/)."
        ),
    )
    _ = parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume incomplete project shards (JSONL upsert by finding uuid).",
    )
    _ = parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reset findings/checkpoint for namespaces in this run.",
    )
    _ = parser.add_argument(
        "--filter",
        dest="extra_filter",
        default=None,
        help=(
            "Additional Finding filter AND-ed with mandatory "
            "MAIN + spec.project_uuid (cannot drop those clauses)."
        ),
    )
    _ = parser.add_argument(
        "--mask",
        default=None,
        help=(
            "Optional Finding field mask (comma-separated). "
            "Default: none (full Finding bodies). Non-empty mask → dict rows."
        ),
    )
    _ = parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Parallel project workers (default: cpu count, 4-16).",
    )
    _ = parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max Finding list pages per project (0 = unlimited).",
    )
    _ = parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Finding list page_size (default: 500; lower if shards 504).",
    )
    add_client_auth_arguments(parser)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export MAIN-context Finding JSONL per project shard "
            "(no category filter by default). "
            "Mandatory filter: CONTEXT_TYPE_MAIN + spec.project_uuid. "
            "Default mask is none (full bodies); pass --mask to project fields. "
            "Auth: env or --token / --api-key+--api-secret (no browser; "
            "refresh first with endor-auth refresh)."
        ),
    )
    _add_flags(parser)
    return parser


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


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``endor-findings-export``."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    namespaces = _resolve_namespaces(args)
    client: Any = client_from_namespace_args(namespaces[0], args)
    result = run_findings_export(
        client,
        namespaces=namespaces,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        max_pages=args.max_pages or None,
        page_size=args.page_size,
        resume=args.resume,
        overwrite=args.overwrite,
        extra_filter=args.extra_filter,
        mask=args.mask,
    )
    print(result.message)
    for ns_result in result.namespace_results:
        print(
            f"  [{ns_result.status}] {ns_result.namespace}: "
            f"{ns_result.findings_path} ({ns_result.finding_rows} rows)"
        )
    if result.summary:
        print(format_summary_line(result.summary))
        print(f"  → {result.summary_path}")
    if result.status in {"error", "partial"}:
        _print_result_errors(result.errors)
        return 1 if result.status == "error" else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
