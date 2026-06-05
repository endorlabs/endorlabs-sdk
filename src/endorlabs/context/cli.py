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
        description="Materialize SDK agent bundle and download platform context."
    )

    _ = parser.add_argument(
        "--output-dir",
        default=".endorlabs-context",
        help="Directory for context files (default: .endorlabs-context).",
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
        "--no-sdk-bundle",
        action="store_false",
        dest="include_sdk_bundle",
        help="Skip materializing the shipped SDK agent bundle.",
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
        choices=("none", "cursor", "claude", "both"),
        default="none",
        help=(
            "Mirror materialized sdk/skills into runtime discovery directories "
            "(default: none)."
        ),
    )

    parser.set_defaults(
        include_openapi=True,
        include_user_docs=True,
        include_sdk_bundle=True,
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Context CLI entrypoint."""
    args = _parse_args(argv)

    status = endorlabs.init(
        output_dir=args.output_dir,
        include_openapi=args.include_openapi,
        include_user_docs=args.include_user_docs,
        include_sdk_bundle=args.include_sdk_bundle,
        max_pages=args.max_pages,
        force=args.force,
        sync_skills=args.sync_skills,
    )

    print("Context bootstrap complete.")

    if status.agent_bundle_path is not None:
        print(f"Agent bundle: {status.agent_bundle_path}")

    if status.context_json_path is not None:
        print(f"Manifest: {status.context_json_path}")

    if status.openapi_path is not None:
        print(f"OpenAPI: {status.openapi_path}")

    if status.user_docs_path is not None:
        print(f"User docs: {status.user_docs_path} ({status.user_docs_count} pages)")

    for target_name, path in sorted(status.synced_skill_paths.items()):
        print(f"{target_name.title()} skills: {path}")


if __name__ == "__main__":
    main()
