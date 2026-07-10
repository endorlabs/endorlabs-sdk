#!/usr/bin/env python3
"""Smoke-test a built wheel in an isolated virtual environment.

Usage:
    uv build
    uv run python devtools/ship/smoke_test_wheel.py
    uv run python devtools/ship/smoke_test_wheel.py --wheel dist/endorlabs-0.1.1-py3-none-any.whl
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _find_wheel(dist_dir: Path, wheel: Path | None) -> Path:
    if wheel is not None:
        if not wheel.is_file():
            msg = f"wheel not found: {wheel}"
            raise FileNotFoundError(msg)
        return wheel
    wheels = sorted(dist_dir.glob("endorlabs-*.whl"))
    if not wheels:
        msg = f"no endorlabs wheel found under {dist_dir}"
        raise FileNotFoundError(msg)
    return wheels[-1]


def main() -> int:
    """Install the wheel in a temp venv and import the public SDK surface."""
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

    wheel = _find_wheel(args.dist_dir, args.wheel)
    print(f"smoke-testing wheel: {wheel.name}")

    with tempfile.TemporaryDirectory(prefix="endorlabs-smoke-") as tmp:
        venv_dir = Path(tmp) / "venv"
        _run([sys.executable, "-m", "venv", str(venv_dir)])

        if sys.platform == "win32":
            python = venv_dir / "Scripts" / "python.exe"
        else:
            python = venv_dir / "bin" / "python"

        _run([str(python), "-m", "pip", "install", str(wheel.resolve())])

        version_proc = _run(
            [
                str(python),
                "-c",
                (
                    "import endorlabs; from endorlabs import Client; "
                    "from importlib.resources import files; "
                    "pkg = files('endorlabs'); "
                    "assert (pkg / 'py.typed').is_file(), 'missing py.typed'; "
                    "assert (pkg / 'client_surface.pyi').is_file(), "
                    "'missing client_surface.pyi'; "
                    "print(endorlabs.__version__)"
                ),
            ]
        )
        version = version_proc.stdout.strip()
        if not version:
            print("smoke test failed: empty __version__", file=sys.stderr)
            return 1
        if args.expect_version is not None and version != args.expect_version:
            print(
                f"smoke test failed: version {version!r} != expected {args.expect_version!r}",
                file=sys.stderr,
            )
            return 1

        print(f"import ok; endorlabs.__version__={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
