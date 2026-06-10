#!/usr/bin/env python3
"""Post-purge verification: history scan + wheel/sdist forbidden path check.

Usage:
    uv run python devtools/history_purge_verify.py
    SETUPTOOLS_SCM_PRETEND_VERSION=0.2.0 uv run python devtools/history_purge_verify.py --build
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TARBALL_FRAGMENTS: tuple[str, ...] = (
    "findings-export",
    "gh-endorlabs",
    ".endorlabs-context/",
    "external_docs/",
)


def _run(cmd: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def history_clean() -> list[str]:
    """Return error strings when discovery paths still appear in git history."""
    proc = _run([sys.executable, "devtools/history_purge_audit.py", "--json"])
    if proc.returncode != 0:
        return [proc.stderr or "history_purge_audit.py failed"]
    import json

    report = json.loads(proc.stdout)
    errors: list[str] = []
    for spec, paths in report.get("path_specs", {}).items():
        if paths:
            errors.append(f"history still contains paths for {spec!r}: {paths[:5]}")
    pattern_hits = report.get("filename_pattern_hits", {})
    for pattern, paths in pattern_hits.items():
        if paths:
            errors.append(f"history still contains pattern {pattern!r}: {paths[:5]}")
    return errors


def tarball_forbidden_members(sdist: Path) -> list[str]:
    """List sdist member paths that match forbidden fragments."""
    bad: list[str] = []
    with tarfile.open(sdist, "r:gz") as archive:
        for member in archive.getmembers():
            name = member.name.replace("\\", "/")
            if any(fragment in name for fragment in FORBIDDEN_TARBALL_FRAGMENTS):
                bad.append(name)
    return bad


def verify_build_artifacts() -> list[str]:
    """Build with pretend version and inspect sdist for forbidden paths."""
    errors: list[str] = []
    build = _run(["uv", "build"])
    if build.returncode != 0:
        return [build.stderr or build.stdout or "uv build failed"]
    sdists = sorted((ROOT / "dist").glob("endorlabs-*.tar.gz"))
    if not sdists:
        return ["no sdist found under dist/"]
    sdist = sdists[-1]
    bad = tarball_forbidden_members(sdist)
    if bad:
        errors.append(f"forbidden paths in {sdist.name}: {bad[:10]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build",
        action="store_true",
        help="Also run uv build and inspect the sdist tarball",
    )
    args = parser.parse_args()

    errors = history_clean()
    if args.build:
        errors.extend(verify_build_artifacts())

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    print("history purge verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
