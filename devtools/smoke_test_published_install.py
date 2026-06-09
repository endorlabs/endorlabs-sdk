#!/usr/bin/env python3
"""Smoke-test a package version installed from TestPyPI in an isolated venv.

Usage:
    uv run python devtools/smoke_test_published_install.py --version 0.1.1
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

TESTPYPI_SIMPLE = "https://test.pypi.org/simple/"
PYPI_SIMPLE = "https://pypi.org/simple/"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def main() -> int:
    """Install endorlabs from TestPyPI and import the public SDK surface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        required=True,
        help="Exact endorlabs version on TestPyPI (e.g. 0.1.1)",
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="endorlabs-testpypi-smoke-") as tmp:
        venv_dir = Path(tmp) / "venv"
        _run([sys.executable, "-m", "venv", str(venv_dir)])

        if sys.platform == "win32":
            python = venv_dir / "Scripts" / "python.exe"
        else:
            python = venv_dir / "bin" / "python"

        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--index-url",
                TESTPYPI_SIMPLE,
                "--extra-index-url",
                PYPI_SIMPLE,
                f"endorlabs=={args.version}",
            ]
        )

        version_proc = _run(
            [
                str(python),
                "-c",
                "import endorlabs; from endorlabs import Client; print(endorlabs.__version__)",
            ]
        )
        installed = version_proc.stdout.strip()
        if installed != args.version:
            print(
                f"version mismatch: expected {args.version}, got {installed!r}",
                file=sys.stderr,
            )
            return 1

        print(f"TestPyPI install ok; endorlabs.__version__={installed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
