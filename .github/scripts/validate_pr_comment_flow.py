#!/usr/bin/env python3
r"""Validate Endor API finding → file/line extraction for PR review comments.

Offline: pass ``--fixture`` with a JSON array of finding dicts.

Live: set ENDOR_* credentials and ``--repo`` / ``--commit-sha``
(or ``GITHUB_REPOSITORY`` / ``GITHUB_SHA``).

Use ``--fail-if-zero-located`` for strict pre-push checks.

Example::

    uv run python .github/scripts/validate_pr_comment_flow.py \\
      --fixture tests/unit/github_scripts/fixtures/pr_comment_flow_golden.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from endor_ci_fetch_scan_findings import load_findings_dicts_for_pr
from endor_scan_findings import extract_location, summarize_location_coverage


def _load_fixture(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"Fixture must be a JSON array: {path}")
    return [row for row in data if isinstance(row, dict)]


def main(argv: list[str] | None = None) -> int:
    """CLI entry: print location coverage and optional samples."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="owner/repo for live API fetch",
    )
    parser.add_argument(
        "--commit-sha",
        default=os.environ.get("GITHUB_SHA", ""),
        help="PR head commit for live API fetch",
    )
    parser.add_argument(
        "--head-ref",
        default=os.environ.get("GITHUB_HEAD_REF", ""),
        help="PR head ref for ScanResult / RepositoryVersion matching (live only)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="JSON array of finding dicts (offline golden)",
    )
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=120.0,
        help="ScanResult poll timeout (live only)",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=500,
        help="Max Finding.get calls (live only)",
    )
    parser.add_argument(
        "--scan-result-uuid",
        default="",
        help=(
            "Optional ScanResult UUID (live only): findings from that scan only; "
            "see load_findings_dicts_for_pr."
        ),
    )
    parser.add_argument(
        "--fail-if-zero-located",
        action="store_true",
        help="Exit 1 when no findings have file+line (after extraction)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=2,
        help="Print first N findings' extract_location result for debugging",
    )
    args = parser.parse_args(argv)

    if args.fixture is not None:
        findings = _load_fixture(args.fixture)
        source = f"fixture:{args.fixture}"
    else:
        if not args.repo or not args.commit_sha:
            print(
                "Live mode requires --repo and --commit-sha "
                "(or GITHUB_REPOSITORY and GITHUB_SHA), or use --fixture.",
                file=sys.stderr,
            )
            return 2
        findings = load_findings_dicts_for_pr(
            repo=args.repo,
            head_sha=args.commit_sha,
            head_ref=args.head_ref.strip(),
            poll_timeout_sec=args.poll_timeout,
            max_findings=args.max_findings,
            scan_result_uuid=args.scan_result_uuid.strip() or None,
        )
        source = "live API"

    cov = summarize_location_coverage(findings)
    print(f"Source: {source}")
    print(
        f"Findings: {cov['total']}, with file+line: {cov['with_file_and_line']}, "
        f"without location: {cov['without_location']}"
    )

    n = max(0, args.sample)
    for i, f in enumerate(findings[:n]):
        loc = extract_location(f)
        uid = f.get("uuid", "?")
        print(f"  sample[{i}] uuid={uid} extract_location={loc!r}")

    if (
        args.fail_if_zero_located
        and cov["with_file_and_line"] == 0
        and cov["total"] > 0
    ):
        print(
            "error: no findings had extractable file+line; "
            "check finding_metadata.custom / dependency_file_paths / line fields.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
