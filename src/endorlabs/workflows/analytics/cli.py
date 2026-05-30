"""CLI entrypoint for ``endor-analytics-export-deps``."""

from __future__ import annotations

from .export_dependencies import main


def cli_main() -> int:
    """Invoke the estate dependency export workflow."""
    return main()


if __name__ == "__main__":
    raise SystemExit(cli_main())
