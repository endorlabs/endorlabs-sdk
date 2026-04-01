#!/usr/bin/env python3
"""Post optional in-house PR comments from Endor scan findings metadata."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from endor_scan_findings import (
    extract_findings,
    extract_location,
    normalize_pr_path,
)

SUMMARY_MARKER = "<!-- endorlabs-inhouse-summary -->"


def _gh_request(
    *,
    token: str,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else {}


def _github_blob_link(repo: str, sha: str, file_path: str, line: int) -> str:
    clean_path = normalize_pr_path(file_path).replace("\\", "/")
    encoded_path = urllib.parse.quote(clean_path, safe="/._-")
    return f"https://github.com/{repo}/blob/{sha}/{encoded_path}#L{line}"


def _optional_snippet_line(finding: dict[str, Any]) -> str | None:
    """Return one short snippet line from metadata for inline comment body, if any."""
    spec = finding.get("spec", {}) if isinstance(finding.get("spec"), dict) else {}
    metadata = spec.get("finding_metadata", {})
    if not isinstance(metadata, dict):
        return None
    sec_review = metadata.get("security_review_data", {})
    if not isinstance(sec_review, dict):
        sec_review = {}
    code_snippet = sec_review.get("code_snippet", {})
    if isinstance(code_snippet, dict):
        text = code_snippet.get("text") or code_snippet.get("snippet")
        if isinstance(text, str) and text.strip():
            line = text.strip().splitlines()[0]
            return line[:200] if len(line) > 200 else line
    return None


def build_inline_review_payload(
    finding: dict[str, Any],
    repo: str,
    sha: str,
    marker: str,
) -> dict[str, Any] | None:
    """Build minimal GitHub pull review-comment JSON from location metadata, or None."""
    loc = extract_location(finding)
    if not loc.get("file") or not loc.get("line"):
        return None
    body_lines = [
        marker,
        f"Endor Labs finding `{finding.get('uuid', 'unknown')}`",
        f"Location: `{loc['file']}:{loc['line']}`",
        "[Open code at finding location]"
        f"({_github_blob_link(repo, sha, str(loc['file']), int(loc['line']))})",
    ]
    snippet = _optional_snippet_line(finding)
    if snippet:
        body_lines.append(f"Snippet: `{snippet}`")
    body = "\n".join(body_lines)
    return {
        "body": body,
        "path": str(loc["file"]),
        "line": int(loc["line"]),
        "side": "RIGHT",
        "commit_id": sha,
    }


def _summary_body(findings: list[dict[str, Any]], repo: str, sha: str) -> str:
    lines = [
        SUMMARY_MARKER,
        "## Endor Labs In-House Comment Summary",
        "",
        f"- Findings discovered in scan artifact: `{len(findings)}`",
        "- Line comments are posted only for findings with precise file+line metadata.",
        "",
    ]
    preview = findings[:20]
    if preview:
        lines.append("| Finding UUID | Location | Code Link |")
        lines.append("|---|---|---|")
        for finding in preview:
            loc = extract_location(finding)
            location = (
                f"`{loc['file']}:{loc['line']}`"
                if loc.get("file") and loc.get("line")
                else "_n/a_"
            )
            code_link = "_n/a_"
            if loc.get("file") and loc.get("line"):
                link = _github_blob_link(repo, sha, str(loc["file"]), int(loc["line"]))
                code_link = f"[Open code]({link})"
            lines.append(
                f"| `{finding.get('uuid', 'unknown')}` | {location} | {code_link} |"
            )
    if len(findings) > len(preview):
        lines.append(
            f"\n_... plus {len(findings) - len(preview)} additional findings._"
        )
    return "\n".join(lines)


def _upsert_summary_comment(
    *,
    token: str,
    api_base: str,
    pr_number: int,
    summary: str,
) -> None:
    issue_comments_url = f"{api_base}/issues/{pr_number}/comments?per_page=100"
    existing_comments = _gh_request(token=token, method="GET", url=issue_comments_url)
    summary_comment = next(
        (
            c
            for c in existing_comments
            if isinstance(c, dict) and SUMMARY_MARKER in str(c.get("body", ""))
        ),
        None,
    )
    if summary_comment:
        _gh_request(
            token=token,
            method="PATCH",
            url=f"{api_base}/issues/comments/{summary_comment['id']}",
            payload={"body": summary},
        )
        print(f"Updated summary comment id={summary_comment['id']}.")
    else:
        created = _gh_request(
            token=token,
            method="POST",
            url=f"{api_base}/issues/{pr_number}/comments",
            payload={"body": summary},
        )
        print(f"Created summary comment id={created.get('id')}.")


def _post_inline_review_comments(
    *,
    token: str,
    api_base: str,
    pr_number: int,
    repo: str,
    commit_sha: str,
    located: list[dict[str, Any]],
) -> None:
    review_comments = _gh_request(
        token=token,
        method="GET",
        url=f"{api_base}/pulls/{pr_number}/comments?per_page=100",
    )
    existing_markers = {
        body
        for body in (
            str(comment.get("body", ""))
            for comment in review_comments
            if isinstance(comment, dict)
        )
    }
    for finding in located[:30]:
        loc = extract_location(finding)
        uid = finding.get("uuid")
        fp = loc["file"]
        ln = loc["line"]
        marker = f"<!-- endorlabs-inhouse-finding:{uid}:{fp}:{ln} -->"
        if any(marker in body for body in existing_markers):
            continue
        comment_payload = build_inline_review_payload(finding, repo, commit_sha, marker)
        if comment_payload is None:
            continue
        try:
            _gh_request(
                token=token,
                method="POST",
                url=f"{api_base}/pulls/{pr_number}/comments",
                payload=comment_payload,
            )
        except urllib.error.HTTPError as exc:
            print(f"Skipped line comment for {finding.get('uuid')}: {exc}")


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and post rollup or inline PR comments from scan JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-output", type=Path, required=True)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument(
        "--post-review-comments",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Post per-line review comments "
            "(use --no-post-review-comments with GitHub Checks)."
        ),
    )
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if args.mode == "apply" and not token:
        raise RuntimeError("GITHUB_TOKEN is required in apply mode.")

    if not args.scan_output.exists():
        print(f"Scan output not found: {args.scan_output}. Skipping.")
        return 0

    raw = args.scan_output.read_text(encoding="utf-8").strip()
    if not raw:
        print(f"Scan output is empty: {args.scan_output}. Skipping.")
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(
            f"Scan output is not valid JSON ({args.scan_output}): {exc}. Skipping.",
        )
        return 0
    findings = extract_findings(payload)
    if not findings:
        print("No findings discovered in scan artifact. Skipping comment flow.")
        return 0

    api_base = f"https://api.github.com/repos/{args.repo}"
    summary = _summary_body(findings, args.repo, args.commit_sha)

    located: list[dict[str, Any]] = []
    for f in findings:
        loc = extract_location(f)
        if loc.get("file") and loc.get("line"):
            located.append(f)
    unlocated = len(findings) - len(located)
    print(
        f"Found {len(findings)} findings. "
        f"{len(located)} have precise location metadata, {unlocated} do not."
    )

    if args.mode == "dry-run":
        print("[DRY-RUN] Would upsert rollup PR comment and line comments.")
        return 0

    _upsert_summary_comment(
        token=token,
        api_base=api_base,
        pr_number=args.pr_number,
        summary=summary,
    )

    if args.post_review_comments:
        _post_inline_review_comments(
            token=token,
            api_base=api_base,
            pr_number=args.pr_number,
            repo=args.repo,
            commit_sha=args.commit_sha,
            located=located,
        )
    else:
        print("Skipping per-line review comments (--no-post-review-comments).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
