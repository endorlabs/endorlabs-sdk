#!/usr/bin/env python3
"""Audit git history for paths that must be purged before a public release.

Read-only discovery for proprietary exports, bulk committed docs, and related
blobs. Outputs a redacted path list suitable for ``git filter-repo --invert-paths``.

Usage:
    uv run python devtools/history_purge_audit.py
    uv run python devtools/history_purge_audit.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Path globs / prefixes to scan (expand from discovery hits).
DISCOVERY_PATH_SPECS: tuple[str, ...] = (
    "*findings-export*",
    "*gh-endorlabs*",
    ".endorlabs-context/",
    ".endorlabs-context/docs/",
    ".endorlabs-context/user-docs/",
    ".endorlabs-context/openapi/",
    "external_docs/",
    "external_docs/user-docs/",
)

DEFAULT_INVERT_PATHS: tuple[str, ...] = (
    ".endorlabs-context/",
    "external_docs/",
)

_FILENAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"findings-export", re.I),
    re.compile(r"gh-endorlabs", re.I),
)


def _run_git(args: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def paths_from_log(pathspec: str) -> list[str]:
    """Return unique paths ever touched under *pathspec* in history."""
    proc = _run_git(["log", "--all", "--name-only", "--pretty=format:", "--", pathspec])
    if proc.returncode != 0:
        return []
    paths: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            paths.add(line.replace("\\", "/"))
    return sorted(paths)


def commits_touching(pathspec: str) -> list[str]:
    proc = _run_git(["log", "--all", "--oneline", "--", pathspec])
    if proc.returncode != 0:
        return []
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def scan_filename_patterns() -> dict[str, list[str]]:
    """Find historical paths matching proprietary export filename patterns."""
    proc = _run_git(["log", "--all", "--name-only", "--pretty=format:"])
    if proc.returncode != 0:
        return {}
    hits: dict[str, list[str]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        path = line.strip().replace("\\", "/")
        if not path:
            continue
        for pattern in _FILENAME_PATTERNS:
            if pattern.search(path):
                hits[pattern.pattern].append(path)
    return {k: sorted(set(v)) for k, v in hits.items()}


def build_report() -> dict[str, object]:
    """Collect discovery results for maintainer review."""
    path_hits: dict[str, list[str]] = {}
    commit_hits: dict[str, list[str]] = {}
    for spec in DISCOVERY_PATH_SPECS:
        path_hits[spec] = paths_from_log(spec)
        commit_hits[spec] = commits_touching(spec)

    pattern_hits = scan_filename_patterns()
    invert_candidates: set[str] = set(DEFAULT_INVERT_PATHS)
    for paths in path_hits.values():
        invert_candidates.update(paths)
    for paths in pattern_hits.values():
        invert_candidates.update(paths)

    return {
        "path_specs": path_hits,
        "commits_by_spec": {k: v[:20] for k, v in commit_hits.items() if v},
        "filename_pattern_hits": pattern_hits,
        "suggested_filter_repo_invert_paths": sorted(invert_candidates),
        "filter_repo_example": [
            "git filter-repo --force",
            *(f'  --path "{p}" --invert-paths' for p in sorted(invert_candidates)),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON on stdout",
    )
    args = parser.parse_args()

    if _run_git(["rev-parse", "--git-dir"]).returncode != 0:
        print("not a git repository", file=sys.stderr)
        return 1

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("History purge discovery report")
    print("=" * 40)
    for spec, paths in report["path_specs"].items():
        if not paths:
            continue
        print(f"\n[{spec}] ({len(paths)} path(s))")
        for path in paths[:30]:
            print(f"  - {path}")
        if len(paths) > 30:
            print(f"  ... and {len(paths) - 30} more")

    pattern_hits = report["filename_pattern_hits"]
    if pattern_hits:
        print("\n[filename patterns]")
        for pattern, paths in pattern_hits.items():
            print(f"  pattern {pattern!r}:")
            for path in paths[:20]:
                print(f"    - {path}")

    suggested = report["suggested_filter_repo_invert_paths"]
    print(f"\nSuggested --invert-paths ({len(suggested)}):")
    for path in suggested:
        print(f"  {path}")

    any_hits = any(report["path_specs"].values()) or bool(pattern_hits)
    if not any_hits:
        print("\nNo discovery hits for default path specs (history may already be clean).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
