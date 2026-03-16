"""Canonical model-sync entrypoint.

Run from repo root:
    uv run python scripts/model_sync.py
"""

from __future__ import annotations

import sys

from sync.cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
