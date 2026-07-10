#!/usr/bin/env python3
"""Verify hatch-vcs can resolve a PEP 440 version (fails fast on bad git tags).

Usage:
    uv run python devtools/ship/check_vcs_version.py
    uv run python devtools/ship/check_vcs_version.py --expect 0.2.0
    SETUPTOOLS_SCM_PRETEND_VERSION=0.2.0 uv run python devtools/ship/check_vcs_version.py --release-only --expect 0.2.0
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Tags that break setuptools-scm or confuse git describe (see setuptools-scm #1040).
_FORBIDDEN_TAG_RE = re.compile(
    r"^v\d+\.\d+\.\d+\.dev(?!0$)\d+",  # e.g. v0.1.1.dev19
)
_WARN_TAG_RE = re.compile(
    r"^v\d+\.\d+\.\d+\.(?:dev-build|test\.)",  # experimental naming
)


def _list_local_tags() -> list[str]:
    proc = subprocess.run(
        ["git", "tag", "-l", "v*"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def check_tag_policy(tags: list[str]) -> list[str]:
    """Return human-readable issues for discouraged or forbidden version tags."""
    issues: list[str] = []
    for tag in tags:
        if _FORBIDDEN_TAG_RE.match(tag):
            issues.append(
                f"forbidden tag {tag!r} (custom .devN in tag; use vX.Y.Z.dev0 anchor only)"
            )
        elif _WARN_TAG_RE.match(tag):
            issues.append(
                f"discouraged tag {tag!r} (ignored by git_describe_command; consider deleting)"
            )
    return issues


def resolve_hatch_version(*, root: Path = ROOT) -> str | None:
    """Run ``hatch version`` and return the resolved version, or None on failure."""
    try:
        proc = subprocess.run(
            ["uv", "run", "hatch", "version"],
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
        print(
            "\nSee docs/contributing/release-publishing.md (invalid tags like v0.1.1.dev19).",
            file=sys.stderr,
        )
        return None

    version = (proc.stdout or "").strip()
    if not version:
        print("hatch version returned empty output", file=sys.stderr)
        return None
    return version


def run_check(
    *,
    expect: str | None = None,
    release_only: bool = False,
    root: Path = ROOT,
) -> int:
    """Validate hatch-vcs version resolution; return process exit code."""
    pretend = os.environ.get("SETUPTOOLS_SCM_PRETEND_VERSION", "").strip()
    if release_only and pretend:
        if not expect:
            expect = pretend
    elif not release_only:
        tag_issues = check_tag_policy(_list_local_tags())
        for issue in tag_issues:
            print(f"warning: {issue}", file=sys.stderr)

    version = resolve_hatch_version(root=root)
    if version is None:
        return 1

    if expect is not None and version != expect:
        print(
            f"version mismatch: hatch version {version!r} != expected {expect!r}",
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
        help="Fail unless hatch version equals this PEP 440 string",
    )
    parser.add_argument(
        "--release-only",
        action="store_true",
        help=(
            "Skip tag-archaeology scan; default --expect from "
            "SETUPTOOLS_SCM_PRETEND_VERSION when set"
        ),
    )
    args = parser.parse_args()
    return run_check(expect=args.expect, release_only=args.release_only)


if __name__ == "__main__":
    raise SystemExit(main())
