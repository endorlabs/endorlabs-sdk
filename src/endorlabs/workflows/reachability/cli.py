"""CLI for unified reachability context export."""

from __future__ import annotations

import argparse
import logging

from endorlabs.workflows.reachability.context import (
    ReachabilityContextRequest,
    build_reachability_context,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for reachability context export."""
    parser = argparse.ArgumentParser(
        description="Build a normalized reachability context bundle for one finding or package version."
    )
    parser.add_argument(
        "--tenant", required=True, help="Tenant used for authentication."
    )
    parser.add_argument(
        "--namespace",
        required=True,
        help="Namespace for finding or package-version lookup.",
    )
    parser.add_argument("--finding-uuid", default="", help="Finding UUID to analyze.")
    parser.add_argument("--pv-uuid", default="", help="Importer package-version UUID.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument(
        "--max-pages", type=int, default=10, help="Maximum pages for list operations."
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=200,
        help="List API page size for graph discovery.",
    )
    parser.add_argument(
        "--decode-zstd",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Decode zstd graph payloads into callable/edge summaries.",
    )
    parser.add_argument(
        "--include-oss-callgraph",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch and include oss call graph plane.",
    )
    parser.add_argument(
        "--include-customer-callgraph",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch and include customer call graph plane.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entrypoint for ``endor-reachability-context``."""
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if bool(args.finding_uuid) == bool(args.pv_uuid):
        raise SystemExit("Provide exactly one of --finding-uuid or --pv-uuid.")
    req = ReachabilityContextRequest(
        tenant=args.tenant,
        namespace=args.namespace,
        output_dir=args.output_dir,
        finding_uuid=args.finding_uuid or None,
        pv_uuid=args.pv_uuid or None,
        decode_zstd=args.decode_zstd,
        include_oss_callgraph=args.include_oss_callgraph,
        include_customer_callgraph=args.include_customer_callgraph,
        max_pages=args.max_pages,
        page_size=args.page_size,
    )
    out_path = build_reachability_context(req)
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
