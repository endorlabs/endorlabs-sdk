#!/usr/bin/env python3
"""Post GitHub pull request review comments (unified-diff anchors) from Endor findings.

Submits a **pull request review** (``POST .../pulls/{n}/reviews``) with
``event: COMMENT`` and a ``comments`` array of **pull request review comments**
— not issue comments or commit comments. See
https://docs.github.com/en/rest/pulls/reviews and
https://docs.github.com/en/rest/pulls/comments
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from typing import Any

from endor_ci_fetch_scan_findings import load_findings_dicts_for_pr
from endor_scan_findings import (
    extract_location,
    is_valid_annotation_path,
    normalize_pr_path,
)

# GitHub does not document a hard cap; chunk to reduce 422/payload risk.
_DEFAULT_REVIEW_COMMENTS_PER_REQUEST = 25
_DEFAULT_MAX_INLINE = 30
_GH_PER_PAGE = 100


def _gh_get_json(*, token: str, url: str) -> Any:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else []


def _gh_post_json(
    *,
    token: str,
    url: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    data = json.dumps(payload).encode("utf-8")
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
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        print(
            f"GitHub API POST {exc.code} {exc.reason} {url}\n{err_body}",
        )
        return None
    return json.loads(body) if body else {}


def _github_blob_link(repo: str, sha: str, file_path: str, line: int) -> str:
    clean_path = normalize_pr_path(file_path).replace("\\", "/")
    encoded_path = urllib.parse.quote(clean_path, safe="/._-")
    return f"https://github.com/{repo}/blob/{sha}/{encoded_path}#L{line}"


def iter_pr_file_rows(
    *, token: str, api_base: str, pr_number: int
) -> Iterator[dict[str, Any]]:
    """Yield dict rows from GET pulls/{pr}/files (paginated)."""
    page = 1
    while True:
        q = urllib.parse.urlencode({"per_page": _GH_PER_PAGE, "page": page})
        url = f"{api_base}/pulls/{pr_number}/files?{q}"
        batch = _gh_get_json(token=token, url=url)
        if not isinstance(batch, list) or not batch:
            break
        for row in batch:
            if isinstance(row, dict):
                yield row
        if len(batch) < _GH_PER_PAGE:
            break
        page += 1


def fetch_pr_filenames(*, token: str, api_base: str, pr_number: int) -> set[str]:
    """Return set of `filename` values from GET pulls/{pr}/files (paginated)."""
    names: set[str] = set()
    for row in iter_pr_file_rows(token=token, api_base=api_base, pr_number=pr_number):
        fn = row.get("filename")
        if isinstance(fn, str) and fn:
            names.add(fn.replace("\\", "/"))
    return names


_HUNK_NEW_START_RE = re.compile(r"^@@(?:\s+-\d+(?:,\d+)?\s+)?\+(\d+)(?:,(\d+))?\s+@@")


def parse_patch_right_side_line_numbers(patch: str) -> set[int]:
    """1-based new-file line numbers that appear in a unified diff (RIGHT / side=RIGHT).

    GitHub only accepts pull request review comments on lines present in the PR patch.
    Tools like Qodo anchor on added/changed hunks; Endor file:line often points outside
    the visible diff, which yields HTTP 422 and no visible thread.
    """
    valid: set[int] = set()
    i = 0
    plines = patch.split("\n")
    while i < len(plines):
        raw = plines[i]
        if raw.startswith("@@"):
            m = _HUNK_NEW_START_RE.match(raw)
            if not m:
                i += 1
                continue
            new_line = int(m.group(1))
            i += 1
            while i < len(plines) and not plines[i].startswith("@@"):
                dl = plines[i]
                if not dl:
                    i += 1
                    continue
                tag = dl[0]
                if tag in (" ", "+"):
                    valid.add(new_line)
                    new_line += 1
                elif tag in ("-", "\\"):
                    pass
                i += 1
            continue
        i += 1
    return valid


def fetch_pr_diff_right_lines_by_path(
    *, token: str, api_base: str, pr_number: int
) -> dict[str, set[int] | None]:
    """Map PR filename to RIGHT-side line numbers in the patch, or None if omitted."""
    out: dict[str, set[int] | None] = {}
    for row in iter_pr_file_rows(token=token, api_base=api_base, pr_number=pr_number):
        fn = row.get("filename")
        if not isinstance(fn, str) or not fn:
            continue
        key = fn.replace("\\", "/")
        patch = row.get("patch")
        if isinstance(patch, str) and patch.strip():
            out[key] = parse_patch_right_side_line_numbers(patch)
        else:
            out[key] = None
    return out


def filter_comments_to_pr_diff(
    comment_objects: list[dict[str, Any]],
    preview_snippets: list[str | None],
    diff_right_lines_by_path: dict[str, set[int] | None],
) -> tuple[list[dict[str, Any]], list[str | None], int]:
    """Drop comments whose line range is outside the PR unified diff."""
    kept_o: list[dict[str, Any]] = []
    kept_s: list[str | None] = []
    skipped = 0
    for obj, snip in zip(comment_objects, preview_snippets, strict=True):
        if comment_fits_pr_diff_hunk(obj, diff_right_lines_by_path):
            kept_o.append(obj)
            kept_s.append(snip)
        else:
            skipped += 1
    return kept_o, kept_s, skipped


def comment_fits_pr_diff_hunk(
    obj: dict[str, Any],
    diff_right_lines_by_path: dict[str, set[int] | None],
) -> bool:
    """Return True if the review comment's line range lies on RIGHT-side diff lines."""
    path = obj.get("path")
    if not isinstance(path, str):
        return False
    if path not in diff_right_lines_by_path:
        return False
    allowed = diff_right_lines_by_path[path]
    if allowed is None:
        # File in PR but GitHub omitted `patch` (binary/large); cannot validate hunks.
        return True
    try:
        end = int(obj["line"])
        start = int(obj.get("start_line", end))
    except (TypeError, ValueError, KeyError):
        return False
    if start > end:
        start, end = end, start
    return all(ln in allowed for ln in range(start, end + 1))


def resolve_path_to_pr_file(raw_path: str, pr_filenames: set[str]) -> str | None:
    """Map finding path to a PR changed file path, or None if not in the diff."""
    normalized = normalize_pr_path(str(raw_path)).replace("\\", "/").lstrip("./")
    if normalized in pr_filenames:
        return normalized
    suffix = "/" + normalized
    suffix_hits = [f for f in pr_filenames if f == normalized or f.endswith(suffix)]
    if len(suffix_hits) == 1:
        return suffix_hits[0]
    if len(suffix_hits) > 1:
        return None
    base = normalized.split("/")[-1]
    base_suffix = "/" + base
    matches = [f for f in pr_filenames if f.endswith(base_suffix) or f == base]
    if len(matches) == 1:
        return matches[0]
    return None


def list_existing_review_comment_bodies(
    *, token: str, api_base: str, pr_number: int
) -> set[str]:
    """Bodies of existing pull request review comments.

    Fetched via ``GET .../pulls/{n}/comments``.
    """
    bodies: set[str] = set()
    page = 1
    while True:
        q = urllib.parse.urlencode({"per_page": _GH_PER_PAGE, "page": page})
        url = f"{api_base}/pulls/{pr_number}/comments?{q}"
        batch = _gh_get_json(token=token, url=url)
        if not isinstance(batch, list) or not batch:
            break
        for row in batch:
            if isinstance(row, dict):
                b = row.get("body")
                if isinstance(b, str):
                    bodies.add(b)
        if len(batch) < _GH_PER_PAGE:
            break
        page += 1
    return bodies


def _code_snippet_text(finding: dict[str, Any]) -> str | None:
    """Full code_snippet text from finding metadata, if any."""
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
            return text.strip()
    return None


def _optional_snippet_line(finding: dict[str, Any]) -> str | None:
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


def _finding_summary_one_line(finding: dict[str, Any]) -> str | None:
    spec = finding.get("spec", {}) if isinstance(finding.get("spec"), dict) else {}
    s = spec.get("summary")
    if isinstance(s, str) and s.strip():
        return s.strip().splitlines()[0][:500]
    return None


def _line_as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return int(str(value).strip())


def build_review_comment_body(
    finding: dict[str, Any],
    repo: str,
    sha: str,
    resolved_path: str,
    line: int,
    marker: str,
) -> str:
    """Markdown body for one pull request review comment (includes dedupe marker)."""
    spec = finding.get("spec", {}) if isinstance(finding.get("spec"), dict) else {}
    level = spec.get("level", "n/a")
    meta_parts = [f"`{finding.get('uuid', 'unknown')}`", f"`{level}`"]
    cat = spec.get("category")
    if isinstance(cat, str) and cat.strip():
        meta_parts.append(f"`{cat.strip()}`")
    lines = [
        marker,
        "**Endor Labs** · " + " · ".join(meta_parts),
    ]
    summ = _finding_summary_one_line(finding)
    if summ:
        lines.append(summ)
    lines.append(
        f"[View on branch]({_github_blob_link(repo, sha, resolved_path, line)})"
    )
    snippet = _optional_snippet_line(finding)
    if snippet:
        lines.append(f"`{snippet}`")
    return "\n\n".join(lines)


def build_review_comment_object(
    finding: dict[str, Any],
    repo: str,
    sha: str,
    resolved_path: str,
    loc: dict[str, Any],
    marker: str,
) -> dict[str, Any] | None:
    """One review-comment object: path, line, side, body."""
    line = loc.get("line")
    if line is None:
        return None
    try:
        end_line = loc.get("line_end")
        start = _line_as_int(line)
        body = build_review_comment_body(
            finding, repo, sha, resolved_path, start, marker
        )
        obj: dict[str, Any] = {
            "path": resolved_path,
            "line": start,
            "side": "RIGHT",
            "body": body,
        }
        if end_line is not None:
            end = _line_as_int(end_line)
            lo, hi = (start, end) if start <= end else (end, start)
            if hi > lo:
                obj["start_line"] = lo
                obj["line"] = hi
                obj["start_side"] = "RIGHT"
        return obj
    except (TypeError, ValueError):
        return None


def submit_pull_request_reviews(
    *,
    token: str,
    api_base: str,
    pr_number: int,
    commit_sha: str,
    comment_objects: list[dict[str, Any]],
    batch_size: int,
) -> int:
    """Submit pull request reviews; return count of submitted reviews."""
    url = f"{api_base}/pulls/{pr_number}/reviews"
    submitted = 0
    for i in range(0, len(comment_objects), batch_size):
        chunk = comment_objects[i : i + batch_size]
        payload: dict[str, Any] = {
            "commit_id": commit_sha,
            "event": "COMMENT",
            "body": (
                f"**Endor Labs** — {len(chunk)} pull request review comment(s) "
                f"in this batch (automated CI)."
            ),
            "comments": chunk,
        }
        result = _gh_post_json(token=token, url=url, payload=payload)
        if result is not None:
            submitted += 1
            print(f"Submitted pull request review with {len(chunk)} review comment(s).")
        else:
            print(
                f"Batch review failed for {len(chunk)} comment(s); "
                "trying per-comment fallback.",
            )
            for c in chunk:
                fb_payload: dict[str, Any] = {
                    "body": c["body"],
                    "path": c["path"],
                    "line": c["line"],
                    "side": c["side"],
                    "commit_id": commit_sha,
                }
                if "start_line" in c:
                    fb_payload["start_line"] = c["start_line"]
                    fb_payload["start_side"] = c["start_side"]
                fb = _gh_post_json(
                    token=token,
                    url=f"{api_base}/pulls/{pr_number}/comments",
                    payload=fb_payload,
                )
                if fb is not None:
                    pth = c.get("path")
                    ln = c.get("line")
                    print(f"Posted fallback pull request review comment on {pth}:{ln}.")
    return submitted


def _code_region_fence(
    path: str, start_line: int, end_line: int, snippet: str | None
) -> str:
    """GitHub-flavored fenced block with path/line span (visible in Actions logs)."""
    fence_open = f"```{start_line}:{end_line}:{path}"
    if snippet and snippet.strip():
        body = snippet.strip()
    else:
        body = "(no code_snippet text in finding metadata)"
    return f"{fence_open}\n{body}\n```"


def emit_inline_comment_plan_to_log(
    *,
    comment_objects: list[dict[str, Any]],
    preview_snippets: list[str | None],
) -> None:
    """Print each planned inline comment with a code-region fence and full body."""
    if len(preview_snippets) != len(comment_objects):
        raise ValueError("preview_snippets must align with comment_objects")
    use_groups = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    for i, (obj, snip) in enumerate(
        zip(comment_objects, preview_snippets, strict=True), start=1
    ):
        path = str(obj.get("path") or "")
        end_line = obj.get("line")
        start_line = obj.get("start_line", end_line)
        try:
            s_ln = int(start_line) if start_line is not None else 0
            e_ln = int(end_line) if end_line is not None else s_ln
        except (TypeError, ValueError):
            s_ln, e_ln = 0, 0
        title = f"Finding inline #{i}: {path}:{s_ln}" + (
            f"-{e_ln}" if e_ln != s_ln else ""
        )
        if use_groups:
            print(f"::group::{title}")
        else:
            print(f"\n--- {title} ---")
        print(_code_region_fence(path, s_ln, e_ln, snip))
        print("Comment body:")
        print(str(obj.get("body") or ""))
        if use_groups:
            print("::endgroup::")


def prepare_inline_comment_objects(
    findings: list[dict[str, Any]],
    *,
    pr_files: set[str],
    existing_bodies: set[str],
    repo: str,
    commit_sha: str,
    max_inline: int,
    check_existing: bool,
) -> tuple[list[dict[str, Any]], int, int, int, list[str | None]]:
    """Build review ``comments`` payloads, path/summary counts, and log snippets."""
    located: list[dict[str, Any]] = []
    for f in findings:
        loc = extract_location(f)
        rf = loc.get("file")
        if (
            rf is not None
            and loc.get("line") is not None
            and is_valid_annotation_path(str(rf))
        ):
            located.append(f)
    n_unlocated = len(findings) - len(located)
    comment_objects: list[dict[str, Any]] = []
    preview_snippets: list[str | None] = []
    skipped_path = 0
    for finding in located:
        if len(comment_objects) >= max_inline:
            break
        loc = extract_location(finding)
        raw_file = str(loc["file"])
        if pr_files:
            resolved = resolve_path_to_pr_file(raw_file, pr_files)
            if not resolved:
                skipped_path += 1
                continue
        else:
            resolved = normalize_pr_path(raw_file).replace("\\", "/").lstrip("./")
        if not is_valid_annotation_path(resolved):
            skipped_path += 1
            continue
        uid = finding.get("uuid")
        fp = resolved
        ln = loc["line"]
        marker = f"<!-- endorlabs-inhouse-finding:{uid}:{fp}:{ln} -->"
        if check_existing and any(marker in b for b in existing_bodies):
            continue
        obj = build_review_comment_object(
            finding,
            repo,
            commit_sha,
            resolved,
            loc,
            marker,
        )
        if obj is not None:
            comment_objects.append(obj)
            preview_snippets.append(_code_snippet_text(finding))
    return comment_objects, skipped_path, len(located), n_unlocated, preview_snippets


def main(argv: list[str] | None = None) -> int:
    """CLI: post pull request review comments from Endor API findings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=300.0,
        help="Seconds to wait for a terminal ScanResult after the scan.",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=500,
        help="Max findings to hydrate from selected ScanResult UUIDs.",
    )
    parser.add_argument(
        "--max-inline",
        type=int,
        default=_DEFAULT_MAX_INLINE,
        help="Max pull request review comments per run (default 30).",
    )
    parser.add_argument(
        "--review-batch-size",
        type=int,
        default=_DEFAULT_REVIEW_COMMENTS_PER_REQUEST,
        help="Max review comments per POST .../pulls/{n}/reviews request (default 25).",
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument(
        "--head-ref",
        default=os.environ.get("GITHUB_HEAD_REF", ""),
        help="PR head branch ref used for repository-version resolution.",
    )
    parser.add_argument(
        "--repository-version-hint",
        default=os.environ.get("ENDOR_REPOSITORY_VERSION_HINT", ""),
        help="Optional repository-version hint (e.g. Endor check external_id).",
    )
    parser.add_argument(
        "--scan-result-uuid",
        default=os.environ.get("ENDOR_SCAN_RESULT_UUID", ""),
        help=(
            "Optional ScanResult UUID: hydrate findings from that scan only "
            "(must match PR head / repository version). "
            "Default: merge all matching terminal scans. "
            "Override with ENDOR_SCAN_RESULT_UUID."
        ),
    )
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if args.mode == "apply" and not token:
        raise RuntimeError("GITHUB_TOKEN is required in apply mode.")

    findings = load_findings_dicts_for_pr(
        repo=args.repo,
        head_sha=args.commit_sha,
        head_ref=args.head_ref,
        repository_version_hint=(
            args.repository_version_hint if args.repository_version_hint else None
        ),
        scan_result_uuid=(
            args.scan_result_uuid if args.scan_result_uuid.strip() else None
        ),
        poll_timeout_sec=args.poll_timeout,
        max_findings=args.max_findings,
    )

    if not findings:
        print("No findings to post. Skipping.")
        return 0

    api_base = f"https://api.github.com/repos/{args.repo}"
    pr_files: set[str] = set()
    existing_bodies: set[str] = set()
    diff_right_lines_by_path: dict[str, set[int] | None] = {}
    if args.mode == "apply":
        diff_right_lines_by_path = fetch_pr_diff_right_lines_by_path(
            token=token, api_base=api_base, pr_number=args.pr_number
        )
        pr_files = set(diff_right_lines_by_path.keys())
        print(f"PR has {len(pr_files)} changed file(s) for path matching.")
        if not pr_files:
            print(
                "Warning: empty PR file list from API; "
                "falling back to normalized finding paths only.",
            )
        existing_bodies = list_existing_review_comment_bodies(
            token=token, api_base=api_base, pr_number=args.pr_number
        )

    (
        comment_objects,
        skipped_path,
        n_located,
        n_unlocated,
        preview_snippets,
    ) = prepare_inline_comment_objects(
        findings,
        pr_files=pr_files,
        existing_bodies=existing_bodies,
        repo=args.repo,
        commit_sha=args.commit_sha,
        max_inline=args.max_inline,
        check_existing=(args.mode == "apply"),
    )

    before_diff_filter = len(comment_objects)
    skipped_diff = 0
    if args.mode == "apply" and diff_right_lines_by_path:
        comment_objects, preview_snippets, skipped_diff = filter_comments_to_pr_diff(
            comment_objects,
            preview_snippets,
            diff_right_lines_by_path,
        )

    print(
        f"Findings: {len(findings)}, with file+line: {n_located}, "
        f"unlocated: {n_unlocated}, "
        f"candidates (cap/dedupe/path): {before_diff_filter}, "
        f"after PR-diff hunk filter: {len(comment_objects)}, "
        f"skipped (path not in PR): {skipped_path}, "
        f"skipped (line not in diff hunks): {skipped_diff}."
    )
    if skipped_diff:
        print(
            "Note: GitHub only attaches pull request review comments to lines that "
            "appear in the PR unified diff (added/context in hunks). Other lines "
            "return HTTP 422."
        )

    if comment_objects:
        print("Pull request review comment plan (code regions + bodies):")
        emit_inline_comment_plan_to_log(
            comment_objects=comment_objects,
            preview_snippets=preview_snippets,
        )

    if args.mode == "dry-run":
        print(
            "[DRY-RUN] Would submit pull request review(s) with review comments "
            "on the diff."
        )
        return 0

    if not comment_objects:
        print("No pull request review comments to submit.")
        return 0

    submit_pull_request_reviews(
        token=token,
        api_base=api_base,
        pr_number=args.pr_number,
        commit_sha=args.commit_sha,
        comment_objects=comment_objects,
        batch_size=max(1, args.review_batch_size),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
