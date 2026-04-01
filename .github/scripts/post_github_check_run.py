#!/usr/bin/env python3
"""Publish Endor scan findings as a GitHub Check Run with inline annotations."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from endor_scan_findings import (
    extract_findings,
    extract_location,
    normalize_pr_path,
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
    spec = finding.get("spec") if isinstance(finding.get("spec"), dict) else {}
    meta = spec.get("meta") if isinstance(spec.get("meta"), dict) else {}
    name = (
        meta.get("name") or spec.get("rule_name") or str(finding.get("uuid", "finding"))
    )
    text = str(name)[:250]
    return text


def _finding_message(finding: dict[str, Any]) -> str:
    spec = finding.get("spec") if isinstance(finding.get("spec"), dict) else {}
    parts = [
        f"UUID: `{finding.get('uuid', 'unknown')}`",
        f"Level: `{spec.get('level', 'n/a')}`",
    ]
    desc = spec.get("description")
    if isinstance(desc, str) and desc.strip():
        parts.append(desc.strip()[:4000])
    return "\n\n".join(parts)


def _check_conclusion(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "success"
    for f in findings:
        if _finding_annotation_level(f) == "failure":
            return "failure"
    return "neutral"


def build_annotations(
    findings_with_location: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build GitHub Checks API annotation dicts (path, lines, level, message)."""
    out: list[dict[str, Any]] = []
    for finding in findings_with_location:
        loc = extract_location(finding)
        path = normalize_pr_path(str(loc["file"])).replace("\\", "/")
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


def _summary_markdown(
    findings: list[dict[str, Any]],
    annotations_total: int,
    batches_posted: int,
) -> str:
    lines = [
        "## Endor Labs scan findings",
        "",
        f"- **Findings in artifact:** {len(findings)}",
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
    parser.add_argument("--scan-output", type=Path, required=True)
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument(
        "--commit-sha", required=True, help="HEAD SHA for the check run"
    )
    parser.add_argument("--check-name", default=_CHECK_NAME_DEFAULT)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
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
    located: list[dict[str, Any]] = []
    for f in findings:
        loc = extract_location(f)
        if loc.get("file") and loc.get("line") is not None:
            located.append(f)
    annotations = build_annotations(located)
    conclusion = _check_conclusion(findings)

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
