"""CLI entrypoint for ``endor-agent-context`` (project context bundle export)."""

from __future__ import annotations

from .export import main


def cli_main() -> int:
    """Invoke the export workflow (prints manifest path to stdout)."""
    return main()


if __name__ == "__main__":
    raise SystemExit(cli_main())
