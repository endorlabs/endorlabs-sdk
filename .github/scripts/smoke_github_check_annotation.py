#!/usr/bin/env python3
"""Post a minimal GitHub Check Run with one annotation (validates Checks REST + token).

Use this to verify `checks: write`, JSON shape, and PR head SHA **before** debugging
Endor finding payloads. The annotation targets a repo file that must exist on
``head_sha`` (default: ``pyproject.toml`` line 1).

Example (apply)::

    GITHUB_TOKEN=... uv run python .github/scripts/smoke_github_check_annotation.py \\
        --repo owner/repo --commit-sha <pr_head_sha> --mode apply

Example (print payload only)::

    uv run python .github/scripts/smoke_github_check_annotation.py \\
        --repo owner/repo --commit-sha deadbeef --mode dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from endor_scan_findings import is_valid_annotation_path, normalize_pr_path

_DEFAULT_CHECK_NAME = "Annotation smoke test"


def build_smoke_check_run_body(
    *,
    head_sha: str,
    path: str,
    line: int = 1,
    check_name: str = _DEFAULT_CHECK_NAME,
    message: str = (
        "Smoke test annotation — validates GitHub Checks API payload and permissions."
    ),
) -> dict[str, Any]:
    """Build the JSON body for ``POST .../check-runs`` with a single annotation."""
    path_norm = normalize_pr_path(path.strip()).replace("\\", "/")
    if not is_valid_annotation_path(path_norm):
        raise ValueError(f"Invalid annotation path: {path!r}")
    if line < 1:
        raise ValueError(f"line must be >= 1, got {line}")

    return {
        "name": check_name,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "success",
        "output": {
            "title": check_name,
            "summary": (
                "## Checks API smoke\n\n"
                "One synthetic annotation to validate REST, token scopes, and head SHA."
            ),
            "annotations": [
                {
                    "path": path_norm,
                    "start_line": line,
                    "end_line": line,
                    "annotation_level": "notice",
                    "message": message,
                    "title": "Smoke",
                }
            ],
        },
    }


def _gh_post_check_run(
    *,
    token: str,
    owner: str,
    repo: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{owner}/{repo}/check-runs"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} {exc.reason}: {err_body}") from exc
    return json.loads(raw) if raw else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument(
        "--commit-sha", required=True, help="commit SHA (use PR head SHA)"
    )
    parser.add_argument(
        "--path",
        default="pyproject.toml",
        help="Repo-relative file for the annotation (must exist on commit)",
    )
    parser.add_argument(
        "--line",
        type=int,
        default=1,
        help="1-based line for start_line and end_line",
    )
    parser.add_argument(
        "--check-name",
        default=_DEFAULT_CHECK_NAME,
        help="Check run name (distinct from Endor Labs findings check)",
    )
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    args = parser.parse_args(argv)

    owner, _, repo_name = args.repo.partition("/")
    if not repo_name:
        print("ERROR: --repo must be owner/repo", file=sys.stderr)
        return 2

    try:
        body = build_smoke_check_run_body(
            head_sha=args.commit_sha.strip(),
            path=args.path,
            line=args.line,
            check_name=args.check_name,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.mode == "dry-run":
        print(json.dumps(body, indent=2))
        print(
            "[DRY-RUN] No request sent. Use --mode apply with GITHUB_TOKEN to post.",
            file=sys.stderr,
        )
        return 0

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN is required for apply mode.", file=sys.stderr)
        return 2

    created = _gh_post_check_run(token=token, owner=owner, repo=repo_name, body=body)
    cid = created.get("id", "?")
    html = created.get("html_url", "")
    print(f"Created check run id={cid} html_url={html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
