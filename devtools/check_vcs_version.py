#!/usr/bin/env python3
"""Verify hatch-vcs can resolve a PEP 440 version (fails fast on bad git tags).

Usage:
    uv run python devtools/check_vcs_version.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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


def _check_tag_policy(tags: list[str]) -> list[str]:
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


def main() -> int:
    """Run ``hatch version`` and print the resolved version or exit 1."""
    tag_issues = _check_tag_policy(_list_local_tags())
    for issue in tag_issues:
        print(f"warning: {issue}", file=sys.stderr)

    try:
        proc = subprocess.run(
            ["uv", "run", "hatch", "version"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("uv not found on PATH", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout or str(exc), file=sys.stderr)
        print(
            "\nSee docs/contributing/release-publishing.md (invalid tags like v0.1.1.dev19).",
            file=sys.stderr,
        )
        return 1

    version = (proc.stdout or "").strip()
    if not version:
        print("hatch version returned empty output", file=sys.stderr)
        return 1

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
