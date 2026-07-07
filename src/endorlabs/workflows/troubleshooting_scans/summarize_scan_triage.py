"""Build a markdown triage summary from troubleshooting scan artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from endorlabs.workflows.wire_access import as_dict, dict_str, nested_dict, nested_str

from .common import (
    default_troubleshooting_output_dir,
    root_tenant,
    write_json,
    write_text,
)


def _dict_list(d: dict[str, Any], key: str) -> list[dict[str, Any]]:
    raw = d.get(key)
    if not isinstance(raw, list):
        return []
    return [
        cast("dict[str, Any]", item)
        for item in cast("list[Any]", raw)
        if isinstance(item, dict)
    ]


def _first_dict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[0] if rows else {}


def _load_json(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"Artifact is not a JSON object: {path}")
    return cast("dict[str, Any]", data)


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
    p.add_argument(
        "--output-dir",
        default=default_troubleshooting_output_dir(),
        help="Output directory",
    )
    p.add_argument("--timestamped", action="store_true")
    return p


def _latest_scan_summary(results_artifact: dict[str, Any]) -> dict[str, Any]:
    return _first_dict(_dict_list(results_artifact, "scan_results_summary"))


def _error_entries(logs_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for message in _dict_list(logs_artifact, "messages"):
        level = dict_str(message, "level")
        payload = as_dict(message.get("json_payload"))
        payload_level = dict_str(payload, "level")
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


def _value_excerpt(value: Any, *, max_len: int = 320) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(value)
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def _latest_scan_raw(
    results_artifact: dict[str, Any], scan_uuid: str | None = None
) -> dict[str, Any]:
    scans = _dict_list(results_artifact, "scan_results")
    if not scans:
        return {}
    if scan_uuid:
        for candidate in scans:
            if dict_str(candidate, "uuid") == scan_uuid:
                return candidate
    return scans[0]


def _extract_log_evidence(
    logs_artifact: dict[str, Any], *, max_entries: int = 8
) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for message in _dict_list(logs_artifact, "messages"):
        payload = as_dict(message.get("json_payload"))
        level = dict_str(message, "level")
        payload_level = dict_str(payload, "level")
        norm_level = payload_level.lower() or level.lower()
        if norm_level not in {"error", "warn", "warning", "fatal", "log_level_error"}:
            continue
        entries.append(
            {
                "path": "messages[].json_payload.msg",
                "value": _value_excerpt(payload.get("msg") or ""),
                "source": "scan_logs_artifact",
            }
        )
        if len(entries) >= max_entries:
            break
    return entries


def _signature_tags(
    scan_raw: dict[str, Any], logs_artifact: dict[str, Any]
) -> list[str]:
    tags: set[str] = set()
    spec = nested_dict(scan_raw, "spec")
    provisioning = nested_dict(spec, "provisioning_result")
    blob = " ".join(
        [
            dict_str(provisioning, "error"),
            json.dumps(logs_artifact.get("messages") or [], ensure_ascii=False).lower(),
        ]
    ).lower()
    if "hash sum mismatch" in blob:
        tags.add("repo_index_hash_mismatch")
    if "bazel" in blob and "build did not complete successfully" in blob:
        tags.add("build_orchestration_failure")
    if "gradle init" in blob:
        tags.add("manifest_or_tooling_discovery_issue")
    if "unable to generate manifest path" in blob:
        tags.add("manifest_generation_failure")
    if dict_str(spec, "status") == "STATUS_PARTIAL_SUCCESS":
        tags.add("partial_scan_coverage")
    return sorted(tags)


def _build_evidence_payload(
    *,
    tenant: str,
    project_uuid: str,
    project_name: str,
    namespace: str,
    scan_uuid: str,
    results_artifact: dict[str, Any],
    logs_artifact: dict[str, Any],
) -> dict[str, Any]:
    scan_raw = _latest_scan_raw(results_artifact, scan_uuid)
    spec = nested_dict(scan_raw, "spec")
    provisioning = nested_dict(spec, "provisioning_result")
    stats = nested_dict(spec, "stats")

    status_evidence = [
        {
            "path": "scan_results[].spec.status",
            "value": _value_excerpt(spec.get("status")),
            "source": "scan_results_artifact",
        },
        {
            "path": "scan_results[].spec.type",
            "value": _value_excerpt(spec.get("type")),
            "source": "scan_results_artifact",
        },
    ]
    provisioning_evidence = [
        {
            "path": "scan_results[].spec.provisioning_result.exit_code",
            "value": _value_excerpt(provisioning.get("exit_code")),
            "source": "scan_results_artifact",
        },
        {
            "path": "scan_results[].spec.provisioning_result.error",
            "value": _value_excerpt(provisioning.get("error")),
            "source": "scan_results_artifact",
        },
    ]
    stats_evidence = [
        {
            "path": "scan_results[].spec.stats.scan_success",
            "value": _value_excerpt(stats.get("scan_success")),
            "source": "scan_results_artifact",
        },
        {
            "path": "scan_results[].spec.stats.scan_failures",
            "value": _value_excerpt(stats.get("scan_failures")),
            "source": "scan_results_artifact",
        },
        {
            "path": "scan_results[].spec.stats.package_versions",
            "value": _value_excerpt(stats.get("package_versions")),
            "source": "scan_results_artifact",
        },
        {
            "path": "scan_results[].spec.stats.dependency_analysis_num_full",
            "value": _value_excerpt(stats.get("dependency_analysis_num_full")),
            "source": "scan_results_artifact",
        },
        {
            "path": "scan_results[].spec.stats.dependency_analysis_num_approximate",
            "value": _value_excerpt(stats.get("dependency_analysis_num_approximate")),
            "source": "scan_results_artifact",
        },
    ]
    log_evidence = _extract_log_evidence(logs_artifact)

    return {
        "tenant": tenant,
        "namespace": namespace,
        "project_uuid": project_uuid,
        "project_name": project_name or None,
        "scan_result_uuid": scan_uuid,
        "status_evidence": status_evidence,
        "provisioning_evidence": provisioning_evidence,
        "stats_evidence": stats_evidence,
        "log_evidence": log_evidence,
        "matched_signatures": _signature_tags(scan_raw, logs_artifact),
    }


def _error_markdown_rows(errors: list[dict[str, Any]], max_errors: int) -> list[str]:
    rows: list[str] = []
    for idx, entry in enumerate(errors[:max_errors], start=1):
        payload = as_dict(entry.get("json_payload"))
        ts = dict_str(entry, "timestamp")
        code = dict_str(payload, "code")
        msg = dict_str(payload, "msg")
        package_name = dict_str(payload, "package_name")
        resolution_error = _first_line(dict_str(payload, "resolution_error"))
        stderr = _first_line(dict_str(payload, "stderr"))
        details: list[str] = []
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


def _project_name_from_search(search_artifact: dict[str, Any] | None) -> str:
    if search_artifact is None:
        return ""
    projects = _dict_list(search_artifact, "projects")
    if not projects:
        return ""
    return nested_str(projects[0], "meta", "name")


def _evidence_markdown_lines(evidence_payload: dict[str, Any], key: str) -> list[str]:
    return [
        f"  - `{dict_str(entry, 'path')}` -> `{dict_str(entry, 'value')}` "
        f"(source: `{dict_str(entry, 'source')}`)"
        for entry in _dict_list(evidence_payload, key)
    ]


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
    evidence_payload: dict[str, Any],
) -> str:
    latest = _latest_scan_summary(results_artifact)
    errors = _error_entries(logs_artifact)

    project_uuid = dict_str(logs_artifact, "project_uuid") or dict_str(
        results_artifact, "project_uuid"
    )
    scan_uuid = dict_str(logs_artifact, "scan_result_uuid") or dict_str(latest, "uuid")
    namespace = dict_str(logs_artifact, "namespace") or dict_str(latest, "namespace")
    project_name = _project_name_from_search(search_artifact)

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
        f"- scan_status: `{dict_str(latest, 'status')}`",
        f"- scan_exit_code: `{dict_str(latest, 'exit_code')}`",
        f"- scan_success: `{dict_str(latest, 'scan_success')}`",
        f"- scan_failures: `{dict_str(latest, 'scan_failures')}`",
        f"- endorctl_version: `{dict_str(latest, 'endorctl_version')}`",
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
        lines.append("- No error-level log entries detected in scan log artifact.")

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
            "## Evidence (Field Paths)",
            "",
            "- status_evidence:",
        ]
    )
    lines.extend(_evidence_markdown_lines(evidence_payload, "status_evidence"))
    lines.append("- provisioning_evidence:")
    lines.extend(_evidence_markdown_lines(evidence_payload, "provisioning_evidence"))
    lines.append("- stats_evidence:")
    lines.extend(_evidence_markdown_lines(evidence_payload, "stats_evidence"))
    lines.append("- log_evidence:")
    lines.extend(_evidence_markdown_lines(evidence_payload, "log_evidence"))
    signatures_raw = evidence_payload.get("matched_signatures")
    if isinstance(signatures_raw, list) and signatures_raw:
        signatures = [str(tag) for tag in cast("list[Any]", signatures_raw)]
        lines.append("- matched_signatures:")
        lines.extend(f"  - `{tag}`" for tag in signatures)

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
    """Run the module CLI and return exit code."""
    args = _build_parser().parse_args()

    results_artifact = _load_json(args.scan_results_artifact)
    logs_artifact = _load_json(args.scan_logs_artifact)
    search_artifact = (
        _load_json(args.project_search_artifact)
        if args.project_search_artifact
        else None
    )

    latest = _latest_scan_summary(results_artifact)
    project_uuid = dict_str(logs_artifact, "project_uuid") or dict_str(
        results_artifact, "project_uuid"
    )
    namespace = dict_str(logs_artifact, "namespace") or dict_str(latest, "namespace")
    scan_uuid = dict_str(logs_artifact, "scan_result_uuid") or dict_str(latest, "uuid")
    project_name = _project_name_from_search(search_artifact)
    evidence_payload = _build_evidence_payload(
        tenant=args.tenant,
        project_uuid=project_uuid,
        project_name=project_name,
        namespace=namespace,
        scan_uuid=scan_uuid,
        results_artifact=results_artifact,
        logs_artifact=logs_artifact,
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
        evidence_payload=evidence_payload,
    )

    scan_uuid_out = scan_uuid or "unknown-scan"
    root = root_tenant(args.tenant)
    out_path = write_text(
        output_dir=Path(args.output_dir),
        root_tenant_name=root,
        object_kind="scan_triage",
        object_uuid=scan_uuid_out,
        purpose="summary",
        text=md,
        extension=".md",
        timestamped=args.timestamped,
    )
    evidence_path = write_json(
        output_dir=Path(args.output_dir),
        root_tenant_name=root,
        object_kind="scan_triage_evidence",
        object_uuid=scan_uuid_out,
        purpose="summary",
        payload=evidence_payload,
        timestamped=args.timestamped,
    )
    print(
        json.dumps(
            {"summary_markdown": str(out_path), "summary_evidence": str(evidence_path)}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
