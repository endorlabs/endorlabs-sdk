#!/usr/bin/env python3
"""Smoke-test a built wheel in an isolated virtual environment.

Usage:
    uv build
    uv run python devtools/ship/smoke_test_wheel.py
    uv run python devtools/ship/smoke_test_wheel.py --wheel dist/endorlabs-0.1.1-py3-none-any.whl

Delegates to :mod:`verify_wheel_contents` for manifest/import parity checks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verify_wheel_contents import run_verify  # noqa: E402


def main() -> int:
    """Install the wheel in a temp venv and verify shipped contents."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel",
        type=Path,
        default=None,
        help="Path to a built wheel (default: newest dist/endorlabs-*.whl)",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=ROOT / "dist",
        help="Directory containing built wheels",
    )
    parser.add_argument(
        "--expect-version",
        default=None,
        help="Fail unless installed endorlabs.__version__ equals this string",
    )
    args = parser.parse_args()
    return run_verify(
        wheel=args.wheel,
        dist_dir=args.dist_dir,
        expect_version=args.expect_version,
    )


if __name__ == "__main__":
    raise SystemExit(main())
