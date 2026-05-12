"""CLI for local Endor Labs context bootstrap.

Run with:
    uv run endor-context
"""

from __future__ import annotations

import argparse

import endorlabs


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args for context bootstrap."""
    parser = argparse.ArgumentParser(
        description="Download local Endor Labs context files."
    )
    _ = parser.add_argument(
        "--output-dir",
        default=".endorlabs-context",
        help="Directory for downloaded files (default: .endorlabs-context).",
    )
    _ = parser.add_argument(
        "--no-openapi",
        action="store_false",
        dest="include_openapi",
        help="Skip OpenAPI spec download.",
    )
    _ = parser.add_argument(
        "--no-user-docs",
        action="store_false",
        dest="include_user_docs",
        help="Skip user docs download.",
    )
    _ = parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit docs pages downloaded.",
    )
    _ = parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-download even if files already exist.",
    )
    _ = parser.add_argument(
        "--sync-skills",
        choices=("none", "cursor", "claude", "both", "auto"),
        default="none",
        help=(
            "Mirror skills-src into runtime skill discovery directories "
            "(default: none)."
        ),
    )
    parser.set_defaults(include_openapi=True, include_user_docs=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Context CLI entrypoint."""
    args = _parse_args(argv)
    status = endorlabs.init(
        output_dir=args.output_dir,
        include_openapi=args.include_openapi,
        include_user_docs=args.include_user_docs,
        max_pages=args.max_pages,
        force=args.force,
        sync_skills=args.sync_skills,
    )
    print("Context bootstrap complete.")
    if status.openapi_path is not None:
        print(f"OpenAPI: {status.openapi_path}")
    if status.user_docs_path is not None:
        print(f"User docs: {status.user_docs_path} ({status.user_docs_count} pages)")
    for target_name, path in sorted(status.synced_skill_paths.items()):
        print(f"{target_name.title()} skills: {path}")


if __name__ == "__main__":
    main()
