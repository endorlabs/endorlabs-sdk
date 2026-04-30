"""Build a markdown triage summary from troubleshooting scan artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.troubleshooting_scans.common import root_tenant, write_text
except ModuleNotFoundError:
    from common import root_tenant, write_text


def _load_json(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Artifact is not a JSON object: {path}")
    return data


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Build a markdown triage summary from pull_scan_results and "
            "pull_scan_logs JSON artifacts."
        )
    )
    p.add_argument("--tenant", required=True, help="Root tenant namespace")
    p.add_argument(
        "--scan-results-artifact",
        required=True,
        help="Path to pull_scan_results JSON artifact",
    )
    p.add_argument(
        "--scan-logs-artifact",
        required=True,
        help="Path to pull_scan_logs JSON artifact",
    )
    p.add_argument(
        "--project-search-artifact",
        default=None,
        help="Optional path to search_projects JSON artifact",
    )
    p.add_argument(
        "--max-errors",
        type=int,
        default=20,
        help="Maximum number of error entries rendered in markdown",
    )
    p.add_argument("--output-dir", default=".tmp", help="Output directory")
    p.add_argument("--timestamped", action="store_true")
    return p


def _latest_scan_summary(results_artifact: dict[str, Any]) -> dict[str, Any]:
    summaries = results_artifact.get("scan_results_summary") or []
    if not isinstance(summaries, list) or not summaries:
        return {}
    first = summaries[0]
    return first if isinstance(first, dict) else {}


def _error_entries(logs_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in logs_artifact.get("messages") or []:
        if not isinstance(message, dict):
            continue
        level = str(message.get("level") or "")
        payload = message.get("json_payload")
        payload_level = ""
        if isinstance(payload, dict):
            payload_level = str(payload.get("level") or "")
        if level == "LOG_LEVEL_ERROR" or payload_level.lower() == "error":
            out.append(message)
    return out


def _first_line(text: str | None, *, max_len: int = 240) -> str:
    if not text:
        return ""
    line = text.splitlines()[0].strip()
    if len(line) <= max_len:
        return line
    return line[: max_len - 3] + "..."


def _error_markdown_rows(errors: list[dict[str, Any]], max_errors: int) -> list[str]:
    rows: list[str] = []
    for idx, entry in enumerate(errors[:max_errors], start=1):
        payload = entry.get("json_payload") if isinstance(entry, dict) else None
        p = payload if isinstance(payload, dict) else {}
        ts = str(entry.get("timestamp") or "")
        code = str(p.get("code") or "")
        msg = str(p.get("msg") or "")
        package_name = str(p.get("package_name") or "")
        resolution_error = _first_line(str(p.get("resolution_error") or ""))
        stderr = _first_line(str(p.get("stderr") or ""))
        details = []
        if package_name:
            details.append(f"package={package_name}")
        if resolution_error:
            details.append(f"resolution_error={resolution_error}")
        if stderr:
            details.append(f"stderr={stderr}")
        detail_text = "; ".join(details)
        rows.append(
            f"{idx}. **{ts}** `{code or 'error'}` - {msg}"
            + (f"\n   - {detail_text}" if detail_text else "")
        )
    return rows


def _fix_guidance(errors: list[dict[str, Any]]) -> list[str]:
    text_blob = json.dumps(errors, ensure_ascii=False).lower()
    guidance: list[str] = []

    if "dependency-scanning-error" in text_blob:
        guidance.append(
            "- Validate dependency manifests first (for example `requirements.txt`, "
            "`pyproject.toml`, lockfiles); scan logs indicate resolver-level failures."
        )
    if "pypi json api for: python" in text_blob:
        guidance.append(
            "- A `python>=...` requirement appears to be treated as a package lookup; "
            "move interpreter constraints to runtime metadata/config and keep package "
            "dependencies installable."
        )
    if "toolchain-error" in text_blob:
        guidance.append(
            "- Toolchain setup failed in the scan sandbox. Check repository/bootstrap "
            "steps and scan worker network/proxy access for package repo endpoints."
        )
    if "clearsigned file isn't valid" in text_blob or "not signed" in text_blob:
        guidance.append(
            "- Apt repository signature/connectivity error observed; verify network "
            "egress/auth requirements and repository trust chain in scan environment."
        )

    guidance.append(
        "- Reproduce on the same commit/ref and compare scan-time environment fields "
        "(endorctl version, OS/arch, config summary) against a healthy local build."
    )
    guidance.append(
        "- Re-run scan and verify expected deltas (`scan_failures` down, error lines "
        "removed for affected package paths)."
    )
    return guidance


def _build_markdown(
    *,
    tenant: str,
    search_path: str | None,
    results_path: str,
    logs_path: str,
    search_artifact: dict[str, Any] | None,
    results_artifact: dict[str, Any],
    logs_artifact: dict[str, Any],
    max_errors: int,
) -> str:
    latest = _latest_scan_summary(results_artifact)
    errors = _error_entries(logs_artifact)

    project_uuid = (
        str(logs_artifact.get("project_uuid") or "")
        or str(results_artifact.get("project_uuid") or "")
    )
    scan_uuid = str(logs_artifact.get("scan_result_uuid") or latest.get("uuid") or "")
    namespace = str(logs_artifact.get("namespace") or latest.get("namespace") or "")
    project_name = ""
    if isinstance(search_artifact, dict):
        projects = search_artifact.get("projects") or []
        if isinstance(projects, list) and projects:
            first = projects[0]
            if isinstance(first, dict):
                meta = first.get("meta")
                if isinstance(meta, dict):
                    project_name = str(meta.get("name") or "")

    lines: list[str] = [
        "# Troubleshooting Scan Triage Summary",
        "",
        "## Artifacts",
        "",
        (
            f"- project_search: `{search_path}`"
            if search_path
            else "- project_search: n/a"
        ),
        f"- scan_results: `{results_path}`",
        f"- scan_logs: `{logs_path}`",
        "",
        "## Scan Context",
        "",
        f"- tenant: `{tenant}`",
        f"- namespace: `{namespace}`",
        f"- project_uuid: `{project_uuid}`",
        f"- project_name: `{project_name}`" if project_name else "- project_name: n/a",
        f"- scan_result_uuid: `{scan_uuid}`",
        f"- scan_status: `{latest.get('status', '')}`",
        f"- scan_exit_code: `{latest.get('exit_code', '')}`",
        f"- scan_success: `{latest.get('scan_success', '')}`",
        f"- scan_failures: `{latest.get('scan_failures', '')}`",
        f"- endorctl_version: `{latest.get('endorctl_version', '')}`",
        "",
        "## What Is Wrong (citing logs)",
        "",
    ]

    if errors:
        lines.extend(_error_markdown_rows(errors, max_errors=max_errors))
        if len(errors) > max_errors:
            lines.append(
                f"- Note: {len(errors) - max_errors} additional error entries omitted "
                f"(max_errors={max_errors})."
            )
    else:
        lines.append("- No error-level log entries detected in ScanLogs artifact.")

    lines.extend(
        [
            "",
            "## What Can Be Fixed and How",
            "",
            "- Endor docs (first):",
            "  - https://docs.endorlabs.com/developers-api/cli/commands/scan",
            "  - https://docs.endorlabs.com/inventory-insights/scan-history",
            "  - https://docs.endorlabs.com/scan/containers/container-registry-scan",
            "",
        ]
    )
    lines.extend(_fix_guidance(errors))

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Generated from artifact JSON.",
            "- Human review is still required for environment-specific nuances.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = _build_parser().parse_args()

    results_artifact = _load_json(args.scan_results_artifact)
    logs_artifact = _load_json(args.scan_logs_artifact)
    search_artifact = (
        _load_json(args.project_search_artifact)
        if args.project_search_artifact
        else None
    )

    md = _build_markdown(
        tenant=args.tenant,
        search_path=args.project_search_artifact,
        results_path=args.scan_results_artifact,
        logs_path=args.scan_logs_artifact,
        search_artifact=search_artifact,
        results_artifact=results_artifact,
        logs_artifact=logs_artifact,
        max_errors=args.max_errors,
    )

    scan_uuid = str(logs_artifact.get("scan_result_uuid") or "unknown-scan")
    root = root_tenant(args.tenant)
    out_path = write_text(
        output_dir=Path(args.output_dir),
        root_tenant_name=root,
        object_kind="scan_triage",
        object_uuid=scan_uuid,
        purpose="summary",
        text=md,
        extension=".md",
        timestamped=args.timestamped,
    )
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
