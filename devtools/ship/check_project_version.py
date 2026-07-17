#!/usr/bin/env python3
"""Verify committed [project].version matches release expectations.

Usage:
    uv run python devtools/ship/check_project_version.py
    uv run python devtools/ship/check_project_version.py --expect 0.6.0
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_LEGACY_DEV0_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+\.dev0$")


def _list_local_tags() -> list[str]:
    proc = subprocess.run(
        ["git", "tag", "-l", "v*"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def warn_legacy_dev0_tags(tags: list[str]) -> None:
    """Warn when legacy hatch-vcs dev0 anchor tags remain on the remote."""
    for tag in tags:
        if _LEGACY_DEV0_TAG_RE.match(tag):
            print(
                f"warning: legacy dev anchor tag {tag!r} (obsolete after static versioning)",
                file=sys.stderr,
            )


def read_pyproject_version(*, root: Path = ROOT) -> str | None:
    """Return [project].version from pyproject.toml."""
    path = root / "pyproject.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"failed to read {path}: {exc}", file=sys.stderr)
        return None
    except tomllib.TOMLDecodeError as exc:
        print(f"failed to parse {path}: {exc}", file=sys.stderr)
        return None

    project = data.get("project")
    if not isinstance(project, dict):
        print("[project] table missing in pyproject.toml", file=sys.stderr)
        return None

    version = project.get("version")
    if not isinstance(version, str) or not version.strip():
        print(
            "[project].version must be a static PEP 440 string (Endor uv scans TOML only)",
            file=sys.stderr,
        )
        return None
    return version.strip()


def resolve_uv_version(*, root: Path = ROOT) -> str | None:
    """Run ``uv version --short`` and return the resolved version, or None on failure."""
    try:
        proc = subprocess.run(
            ["uv", "version", "--short"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("uv not found on PATH", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        return None

    version = (proc.stdout or "").strip()
    if not version:
        print("uv version --short returned empty output", file=sys.stderr)
        return None
    return version


def run_check(
    *,
    expect: str | None = None,
    warn_tags: bool = True,
    root: Path = ROOT,
) -> int:
    """Validate static project version; return process exit code."""
    if warn_tags:
        warn_legacy_dev0_tags(_list_local_tags())

    version = read_pyproject_version(root=root)
    if version is None:
        return 1

    uv_version = resolve_uv_version(root=root)
    if uv_version is not None and uv_version != version:
        print(
            f"version mismatch: pyproject.toml {version!r} != uv version --short {uv_version!r}",
            file=sys.stderr,
        )
        return 1

    if expect is not None and version != expect:
        print(
            f"version mismatch: project version {version!r} != expected {expect!r}",
            file=sys.stderr,
        )
        return 1

    print(version)
    return 0


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        metavar="VERSION",
        default=None,
        help="Fail unless [project].version equals this PEP 440 string",
    )
    parser.add_argument(
        "--no-tag-warnings",
        action="store_true",
        help="Skip warnings for legacy v*.dev0 anchor tags",
    )
    args = parser.parse_args()
    return run_check(
        expect=args.expect,
        warn_tags=not args.no_tag_warnings,
    )


if __name__ == "__main__":
    raise SystemExit(main())
