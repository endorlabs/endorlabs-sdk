"""CLI for local Endor Labs context bootstrap.

Run with:

    uv run endor-context

"""

from __future__ import annotations

import argparse

import endorlabs
from endorlabs.context._project_context import GITIGNORE_ENTRY
from endorlabs.context.paths import DEFAULT_CONTEXT_DIR


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args for context bootstrap."""
    parser = argparse.ArgumentParser(
        description=(
            "Materialize SDK agent knowledge and optionally download platform "
            f"context under {DEFAULT_CONTEXT_DIR}/."
        )
    )

    _ = parser.add_argument(
        "--output-dir",
        default=DEFAULT_CONTEXT_DIR,
        help=f"Directory for context files (default: {DEFAULT_CONTEXT_DIR}).",
    )

    _ = parser.add_argument(
        "--sync-openapi",
        action="store_true",
        dest="include_openapi",
        help="Download OpenAPI spec to platform/openapi/.",
    )

    _ = parser.add_argument(
        "--no-materialize-agent-knowledge",
        action="store_false",
        dest="include_agent_knowledge",
        help="Skip copying shipped agent knowledge into project sdk/ (default: on).",
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
            "Mirror skills into runtime discovery directories "
            "(default: none; uses materialized sdk/skills/ when present)."
        ),
    )

    _ = parser.add_argument(
        "--print-gitignore-line",
        action="store_true",
        default=False,
        help=f"Print '{GITIGNORE_ENTRY}' and exit.",
    )

    parser.set_defaults(
        include_openapi=False,
        include_agent_knowledge=True,
    )

    return parser.parse_args(argv)


def _has_bootstrap_actions(args: argparse.Namespace) -> bool:
    return bool(
        args.include_openapi
        or args.include_agent_knowledge
        or args.sync_skills != "none"
    )


def main(argv: list[str] | None = None) -> None:
    """Context CLI entrypoint."""
    args = _parse_args(argv)

    if args.print_gitignore_line:
        print(GITIGNORE_ENTRY)
        return

    if not _has_bootstrap_actions(args):
        print("No bootstrap actions requested.")
        print(f"Wheel skills: {endorlabs.agent_knowledge_index_path()}")
        print(
            "Pass --sync-openapi and/or --sync-skills, "
            "or omit --no-materialize-agent-knowledge. "
            "Product docs: configure Docs MCP "
            "(https://docs.endorlabs.com/introduction/docs-mcp-server)."
        )
        return

    status = endorlabs.init(
        output_dir=args.output_dir,
        include_openapi=args.include_openapi,
        include_agent_knowledge=args.include_agent_knowledge,
        force=args.force,
        sync_skills=args.sync_skills,
    )

    print("Context bootstrap complete.")

    if status.context_json_path is not None:
        print(f"Manifest: {status.context_json_path}")

    if status.agent_knowledge_path is not None:
        print(f"Agent knowledge: {status.agent_knowledge_path}")

    if status.openapi_path is not None:
        print(f"OpenAPI: {status.openapi_path}")

    for target_name, path in sorted(status.synced_skill_paths.items()):
        print(f"{target_name.title()} skills: {path}")


if __name__ == "__main__":
    main()
