#!/usr/bin/env python3
"""Publish Endor scan findings as a GitHub Check Run with inline annotations."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any

from endor_ci_fetch_scan_findings import load_findings_dicts_for_pr
from endor_scan_findings import (
    extract_location,
    is_valid_annotation_path,
    normalize_pr_path,
    summarize_location_coverage,
)

# Max annotations per Checks API create/update (docs.github.com REST check-runs).
ANNOTATION_BATCH_SIZE = 50

_CHECK_NAME_DEFAULT = "Endor Labs findings"


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
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} {exc.reason}: {err_body}") from exc
    return json.loads(body) if body else {}


def _line_as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return int(str(value).strip())


def _finding_annotation_level(finding: dict[str, Any]) -> str:
    spec = finding.get("spec") if isinstance(finding.get("spec"), dict) else {}
    level = spec.get("level")
    if level in ("FINDING_LEVEL_CRITICAL", "FINDING_LEVEL_HIGH"):
        return "failure"
    if level == "FINDING_LEVEL_MEDIUM":
        return "warning"
    return "notice"


def _finding_title(finding: dict[str, Any]) -> str:
    meta = finding.get("meta") if isinstance(finding.get("meta"), dict) else {}
    spec = finding.get("spec") if isinstance(finding.get("spec"), dict) else {}
    name = (
        meta.get("name") or spec.get("rule_name") or str(finding.get("uuid", "finding"))
    )
    return str(name)[:250]


def _finding_message(finding: dict[str, Any]) -> str:
    spec = finding.get("spec") if isinstance(finding.get("spec"), dict) else {}
    parts = [
        f"UUID: `{finding.get('uuid', 'unknown')}`",
        f"Level: `{spec.get('level', 'n/a')}`",
    ]
    for key in ("summary", "description", "explanation"):
        text = spec.get(key)
        if isinstance(text, str) and text.strip():
            parts.append(text.strip()[:4000])
            break
    return "\n\n".join(parts)


def _check_conclusion(findings: list[dict[str, Any]]) -> str:
    """Check-run conclusion for the published run (not per-annotation severity).

    Default ``success`` so this informational check does not show a red X on the PR
    when Endor reports HIGH/CRITICAL; those severities still appear on annotations.
    Set env ``ENDOR_GITHUB_CHECK_CONCLUSION`` to ``neutral`` or ``from_findings``
    (legacy: fail the check if any finding maps to annotation_level failure).
    """
    policy = os.environ.get("ENDOR_GITHUB_CHECK_CONCLUSION", "success").strip().lower()
    if policy in ("success", "neutral"):
        return policy
    if policy == "from_findings":
        if not findings:
            return "success"
        for f in findings:
            if _finding_annotation_level(f) == "failure":
                return "failure"
        return "neutral"
    return "success"


def build_annotations(
    findings_with_location: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build GitHub Checks API annotation dicts (path, lines, level, message)."""
    out: list[dict[str, Any]] = []
    for finding in findings_with_location:
        loc = extract_location(finding)
        raw_file = loc.get("file")
        if not isinstance(raw_file, str) or not is_valid_annotation_path(raw_file):
            continue
        path = normalize_pr_path(raw_file).replace("\\", "/")
        if not is_valid_annotation_path(path):
            continue
        start = _line_as_int(loc["line"])
        line_end = loc.get("line_end")
        end = _line_as_int(line_end) if line_end is not None else start
        if end < start:
            end = start
        out.append(
            {
                "path": path,
                "start_line": start,
                "end_line": end,
                "annotation_level": _finding_annotation_level(finding),
                "title": _finding_title(finding),
                "message": _finding_message(finding),
            }
        )
    return out


def maybe_append_smoke_annotation(
    annotations: list[dict[str, Any]],
    *,
    do_append: bool,
    smoke_path: str,
    smoke_line: int,
) -> list[dict[str, Any]]:
    """Append one synthetic ``notice`` annotation when opt-in is set (CI validation).

    GitHub requires ``path`` and lines to be valid for the check run's ``head_sha``.
    Default path ``pyproject.toml`` is expected to exist in this repository.
    """
    if not do_append:
        return annotations
    p = normalize_pr_path(smoke_path.strip()).replace("\\", "/")
    if not is_valid_annotation_path(p):
        print(f"Warning: smoke annotation skipped — invalid path {smoke_path!r}")
        return annotations
    line = max(1, int(smoke_line))
    smoke: dict[str, Any] = {
        "path": p,
        "start_line": line,
        "end_line": line,
        "annotation_level": "notice",
        "title": "Smoke (opt-in)",
        "message": (
            "Opt-in smoke annotation — validates Checks API when anchors are sparse."
        ),
    }
    return [*annotations, smoke]


def smoke_annotation_requested(*, cli_flag: bool) -> bool:
    """True when ``--smoke-annotation`` or ``ENDOR_GITHUB_CHECK_SMOKE`` is enabled."""
    if cli_flag:
        return True
    v = os.environ.get("ENDOR_GITHUB_CHECK_SMOKE", "").strip().lower()
    return v in ("1", "true", "yes")


def _summary_markdown(
    findings: list[dict[str, Any]],
    annotations_total: int,
    batches_posted: int,
) -> str:
    lines = [
        "## Endor Labs scan findings",
        "",
        f"- **Findings:** {len(findings)}",
        (
            f"- **Line-anchored annotations posted:** {annotations_total} "
            f"(batches: {batches_posted}, cap {ANNOTATION_BATCH_SIZE}/request)."
        ),
        "",
    ]
    if len(findings) > annotations_total:
        n = len(findings) - annotations_total
        lines.append(
            f"_Note: {n} finding(s) lack file+line metadata and appear only here._\n"
        )
    preview = findings[:25]
    if preview:
        lines.append("| UUID | Level |")
        lines.append("| --- | --- |")
        for f in preview:
            spec = f.get("spec") if isinstance(f.get("spec"), dict) else {}
            lines.append(f"| `{f.get('uuid', '?')}` | `{spec.get('level', 'n/a')}` |")
    if len(findings) > len(preview):
        lines.append(f"\n_… and {len(findings) - len(preview)} more._")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and create or update a GitHub Check Run with annotations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=300.0,
        help="Seconds to wait for a terminal ScanResult.",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=500,
        help="Max findings to hydrate from selected ScanResult UUIDs.",
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument(
        "--commit-sha", required=True, help="HEAD SHA for the check run"
    )
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
    parser.add_argument("--check-name", default=_CHECK_NAME_DEFAULT)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument(
        "--smoke-annotation",
        action="store_true",
        help=(
            "Append one synthetic annotation (path/line). "
            "Or set env ENDOR_GITHUB_CHECK_SMOKE=1."
        ),
    )
    parser.add_argument(
        "--smoke-path",
        default=os.environ.get("ENDOR_GITHUB_CHECK_SMOKE_PATH", "pyproject.toml"),
        help="Repo-relative path for synthetic annotation.",
    )
    parser.add_argument(
        "--smoke-line",
        type=int,
        default=int(os.environ.get("ENDOR_GITHUB_CHECK_SMOKE_LINE", "1")),
        help="1-based line for synthetic annotation.",
    )
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
        poll_timeout_sec=args.poll_timeout,
        max_findings=args.max_findings,
    )
    cov = summarize_location_coverage(findings)
    print(
        "Location coverage: "
        f"total={cov['total']}, with_file_and_line={cov['with_file_and_line']}, "
        f"without_location={cov['without_location']}"
    )
    located: list[dict[str, Any]] = []
    for f in findings:
        loc = extract_location(f)
        if loc.get("file") and loc.get("line") is not None:
            located.append(f)
    annotations = build_annotations(located)
    smoke_on = smoke_annotation_requested(cli_flag=bool(args.smoke_annotation))
    annotations = maybe_append_smoke_annotation(
        annotations,
        do_append=smoke_on,
        smoke_path=str(args.smoke_path),
        smoke_line=int(args.smoke_line),
    )
    conclusion = _check_conclusion(findings)

    if smoke_on:
        print(
            "Opt-in smoke annotation: enabled "
            f"(path={args.smoke_path!r}, line={args.smoke_line})."
        )
    print(
        f"Findings: {len(findings)}, with file+line: {len(located)} — "
        f"annotations to send: {len(annotations)}, conclusion: {conclusion}"
    )

    if args.mode == "dry-run":
        print(
            "[DRY-RUN] Would create/update GitHub Check Run with batched annotations."
        )
        return 0

    owner, _, repo_name = args.repo.partition("/")
    if not repo_name:
        raise ValueError("--repo must be owner/repo")
    api_base = f"https://api.github.com/repos/{owner}/{repo_name}"

    batches: list[list[dict[str, Any]]] = [
        annotations[i : i + ANNOTATION_BATCH_SIZE]
        for i in range(0, len(annotations), ANNOTATION_BATCH_SIZE)
    ]
    if not batches:
        batches = [[]]

    check_run_id: int | None = None

    for idx, batch in enumerate(batches):
        title = args.check_name
        summary = _summary_markdown(findings, len(annotations), len(batches))
        if idx == 0:
            body: dict[str, Any] = {
                "name": args.check_name,
                "head_sha": args.commit_sha,
                "status": "completed",
                "conclusion": conclusion,
                "output": {
                    "title": title,
                    "summary": summary,
                    "annotations": batch,
                },
            }
            created = _gh_request(
                token=token,
                method="POST",
                url=f"{api_base}/check-runs",
                payload=body,
            )
            check_run_id = int(created["id"])
            nb = len(batch)
            print(
                f"Created check run id={check_run_id}, "
                f"batch {idx + 1}/{len(batches)} ({nb} annotations)."
            )
        else:
            assert check_run_id is not None
            _gh_request(
                token=token,
                method="PATCH",
                url=f"{api_base}/check-runs/{check_run_id}",
                payload={
                    "output": {
                        "title": title,
                        "summary": summary,
                        "annotations": batch,
                    },
                },
            )
            nb = len(batch)
            print(
                f"Patched check run id={check_run_id}, "
                f"batch {idx + 1}/{len(batches)} ({nb} annotations)."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
