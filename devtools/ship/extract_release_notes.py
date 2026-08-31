#!/usr/bin/env python3
"""Build GitHub Release notes from docs/changelog.md.

Usage::

    uv run python devtools/ship/extract_release_notes.py --version 0.7.0
    uv run python devtools/ship/extract_release_notes.py --version 0.7.0 --output release-notes.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_REL = Path("docs/changelog.md")
_VERSION_HEADER_RE = re.compile(r"^## (?P<version>\d+(?:\.\d+)+(?:[a-zA-Z]+\d+)?)\s*$", re.MULTILINE)
_DEFAULT_REPO = "endorlabs/endorlabs-sdk"


def list_changelog_versions(*, root: Path = ROOT) -> list[str]:
    """Return version headers in changelog order (newest first)."""
    text = (root / CHANGELOG_REL).read_text(encoding="utf-8")
    return [match.group("version") for match in _VERSION_HEADER_RE.finditer(text)]


def extract_changelog_section(version: str, *, root: Path = ROOT) -> str:
    """Return markdown body under ``## {version}`` (excludes the header line)."""
    text = (root / CHANGELOG_REL).read_text(encoding="utf-8")
    pattern = rf"^## {re.escape(version)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f"docs/changelog.md missing '## {version}' section")
    body = match.group(1).strip()
    if not body:
        raise ValueError(f"docs/changelog.md '## {version}' section is empty")
    return body


def previous_changelog_version(version: str, *, root: Path = ROOT) -> str | None:
    """Return the semver section immediately after ``version`` in the changelog."""
    versions = list_changelog_versions(root=root)
    try:
        index = versions.index(version)
    except ValueError:
        return None
    if index + 1 >= len(versions):
        return None
    return versions[index + 1]


def format_release_notes(
    version: str,
    *,
    root: Path = ROOT,
    repository: str = _DEFAULT_REPO,
) -> str:
    """Consumer-facing release notes: changelog section + doc/compare footer."""
    body = extract_changelog_section(version, root=root)
    prev = previous_changelog_version(version, root=root)
    lines = [f"## endorlabs {version}", "", body, ""]
    lines.append(
        f"**Changelog:** https://github.com/endorlabs/endorlabs-sdk/blob/v{version}/docs/changelog.md"
    )
    if prev:
        lines.append(
            f"**Compare:** https://github.com/endorlabs/endorlabs-sdk/compare/v{prev}...v{version}"
        )
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, metavar="VERSION")
    parser.add_argument(
        "--output",
        type=Path,
        help="Write notes to this file (default: stdout)",
    )
    parser.add_argument(
        "--repository",
        default=_DEFAULT_REPO,
        help=f"GitHub owner/repo for footer links (default: {_DEFAULT_REPO})",
    )
    args = parser.parse_args(argv)
    try:
        notes = format_release_notes(
            args.version.strip(),
            repository=args.repository.strip(),
        )
    except (OSError, ValueError) as exc:
        print(f"extract_release_notes: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
