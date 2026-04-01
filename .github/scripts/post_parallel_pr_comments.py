#!/usr/bin/env python3
"""Post optional in-house PR comments from Endor scan findings metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

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


def _extract_findings(node: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if "uuid" in value and (
                "finding_metadata" in value
                or "security_review_data" in value
                or ("spec" in value and isinstance(value["spec"], dict))
            ):
                findings.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(node)
    # Deduplicate by uuid when possible.
    dedup: dict[str, dict[str, Any]] = {}
    for finding in findings:
        fid = str(finding.get("uuid", ""))
        if fid:
            dedup[fid] = finding
    return list(dedup.values()) if dedup else findings


def _extract_location(finding: dict[str, Any]) -> dict[str, Any]:
    spec = finding.get("spec", {}) if isinstance(finding.get("spec"), dict) else {}
    metadata = spec.get("finding_metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    sec_review = metadata.get("security_review_data", {})
    if not isinstance(sec_review, dict):
        sec_review = {}
    code_snippet = sec_review.get("code_snippet", {})
    if not isinstance(code_snippet, dict):
        code_snippet = {}

    file_path = code_snippet.get("file") or metadata.get("file") or metadata.get("file_path")
    line = code_snippet.get("line") or metadata.get("line")
    line_end = code_snippet.get("line_end")

    if (not file_path or not line) and isinstance(metadata.get("location"), str):
        m = re.match(r"^(?P<file>.+?):(?P<line>\d+)$", metadata["location"])
        if m:
            file_path = file_path or m.group("file")
            line = line or int(m.group("line"))

    return {"file": file_path, "line": line, "line_end": line_end}


def _normalize_pr_path(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _github_blob_link(repo: str, sha: str, file_path: str, line: int) -> str:
    clean_path = _normalize_pr_path(file_path).replace("\\", "/")
    encoded_path = urllib.parse.quote(clean_path, safe="/._-")
    return f"https://github.com/{repo}/blob/{sha}/{encoded_path}#L{line}"


def _optional_snippet_line(finding: dict[str, Any]) -> str | None:
    """Return a single short line from finding metadata for inline comment body, if any."""
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
    loc = _extract_location(finding)
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
            loc = _extract_location(finding)
            location = (
                f"`{loc['file']}:{loc['line']}`" if loc.get("file") and loc.get("line") else "_n/a_"
            )
            code_link = "_n/a_"
            if loc.get("file") and loc.get("line"):
                link = _github_blob_link(repo, sha, str(loc["file"]), int(loc["line"]))
                code_link = f"[Open code]({link})"
            lines.append(
                f"| `{finding.get('uuid', 'unknown')}` | {location} | {code_link} |"
            )
    if len(findings) > len(preview):
        lines.append(f"\n_... plus {len(findings) - len(preview)} additional findings._")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan-output", type=Path, required=True)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if args.mode == "apply" and not token:
        raise RuntimeError("GITHUB_TOKEN is required in apply mode.")

    if not args.scan_output.exists():
        print(f"Scan output not found: {args.scan_output}. Skipping.")
        return 0

    payload = json.loads(args.scan_output.read_text(encoding="utf-8"))
    findings = _extract_findings(payload)
    if not findings:
        print("No findings discovered in scan artifact. Skipping comment flow.")
        return 0

    api_base = f"https://api.github.com/repos/{args.repo}"
    summary = _summary_body(findings, args.repo, args.commit_sha)

    located = [f for f in findings if _extract_location(f).get("file") and _extract_location(f).get("line")]
    unlocated = len(findings) - len(located)
    print(
        f"Found {len(findings)} findings. "
        f"{len(located)} have precise location metadata, {unlocated} do not."
    )

    if args.mode == "dry-run":
        print("[DRY-RUN] Would upsert rollup PR comment and line comments.")
        return 0

    # Upsert summary issue comment.
    issue_comments_url = f"{api_base}/issues/{args.pr_number}/comments?per_page=100"
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
            url=f"{api_base}/issues/{args.pr_number}/comments",
            payload={"body": summary},
        )
        print(f"Created summary comment id={created.get('id')}.")

    # Best-effort line comments for precise locations with deterministic marker.
    review_comments = _gh_request(
        token=token,
        method="GET",
        url=f"{api_base}/pulls/{args.pr_number}/comments?per_page=100",
    )
    existing_markers = {
        body
        for body in (
            str(comment.get("body", "")) for comment in review_comments if isinstance(comment, dict)
        )
    }
    for finding in located[:30]:
        loc = _extract_location(finding)
        marker = (
            f"<!-- endorlabs-inhouse-finding:{finding.get('uuid')}:{loc['file']}:{loc['line']} -->"
        )
        if any(marker in body for body in existing_markers):
            continue
        comment_payload = build_inline_review_payload(
            finding, args.repo, args.commit_sha, marker
        )
        if comment_payload is None:
            continue
        try:
            _gh_request(
                token=token,
                method="POST",
                url=f"{api_base}/pulls/{args.pr_number}/comments",
                payload=comment_payload,
            )
        except urllib.error.HTTPError as exc:
            # Path/line might not exist in current diff hunk. Keep flow non-fatal.
            print(f"Skipped line comment for {finding.get('uuid')}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
