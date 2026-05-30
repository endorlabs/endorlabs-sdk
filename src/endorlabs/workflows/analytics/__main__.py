"""Run ``python -m endorlabs.workflows.analytics`` (version-cardinality export CLI)."""

from __future__ import annotations

from .cli import cli_main

if __name__ == "__main__":
    raise SystemExit(cli_main())
