"""Compatibility entrypoint for the Endor demo wizard.

Run with:
    uv run main.py

This delegates to `uv run endor-demo`, which now hosts the interactive
wizard flow by default and keeps agent chat mode behind `--agent`.
"""

from __future__ import annotations

from endorlabs.agent.demo_cli import main


if __name__ == "__main__":
    main()
