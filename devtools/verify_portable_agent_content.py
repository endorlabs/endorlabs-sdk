"""Verify agent-skills content avoids committed estate identifiers."""

# ruff: noqa: D103, PERF401, T201

from __future__ import annotations

import re
from pathlib import Path

HEX_UUID_RE = re.compile(r"\b[0-9a-f]{32}\b", re.IGNORECASE)
PLACEHOLDER_UUID_RE = re.compile(r"<[^>]*uuid[^>]*>", re.IGNORECASE)

BANNED_TENANT_SUBSTRINGS = (
    "endor-solutions-tgowan",
    "endor-solutions",
    "-tgowan",
)

ALLOWLIST_LINE_PATTERNS = (
    re.compile(r"schema\.json"),
    re.compile(r"github\.com/endorlabs/endorlabs-sdk"),
    re.compile(r"endorlabs-sdk"),
    re.compile(r"<project-uuid>"),
    re.compile(r"<POLICY_UUID>"),
    re.compile(r"<FINDING_UUID>"),
    re.compile(r"<TEMPLATE_UUID>"),
    re.compile(r"<uuid>"),
    re.compile(r"\{uuid\}"),
)

SCAN_SUFFIXES = {".md", ".mdc", ".py", ".yaml", ".yml"}


def _line_allowed(line: str) -> bool:
    return any(pattern.search(line) for pattern in ALLOWLIST_LINE_PATTERNS)


def verify_portable_agent_content(root: Path) -> list[str]:
    """Return errors for portable-example violations under *root*."""
    errors: list[str] = []
    if not root.is_dir():
        return [f"agent content root not found: {root}"]

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith("schema/"):
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if _line_allowed(line):
                continue
            lowered = line.lower()
            for banned in BANNED_TENANT_SUBSTRINGS:
                if banned in lowered:
                    errors.append(
                        f"{rel}:{line_no}: banned tenant substring {banned!r}"
                    )
            if PLACEHOLDER_UUID_RE.search(line):
                continue
            for match in HEX_UUID_RE.finditer(line):
                errors.append(
                    f"{rel}:{line_no}: literal 32-hex uuid {match.group()!r}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Verify portable agent content.")
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=repo_root / "agent-skills",
        help="Root directory to scan (default: agent-skills/).",
    )
    args = parser.parse_args(argv)
    errors = verify_portable_agent_content(args.root)
    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1
    print("Portable agent content checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
