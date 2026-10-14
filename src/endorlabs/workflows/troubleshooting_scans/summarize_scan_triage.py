"""Build a markdown triage summary from troubleshooting scan artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

from endorlabs.workflows.wire_access import as_dict, dict_str, nested_dict, nested_str

from .common import (
    resolve_troubleshooting_output_dir,
    root_tenant,
    write_json,
    write_text,
)
from .log_payload_extract import (
    diff_selected_toolchain_versions,
    enrich_log_artifact,
    extract_selected_toolchains,
    extract_underlying_errors,
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
        "--secondary-scan-logs-artifact",
        default=None,
        help=(
            "Optional second pull_scan_logs JSON (pair baseline) for "
            "selected-toolchain version deltas"
        ),
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
        default=None,
        help=(
            "Directory for generated artifacts (default: "
            ".endorlabs/tasks/<slug>-<YYYY-MM-DD>/troubleshooting/)."
        ),
    )
    p.add_argument("--timestamped", action="store_true")
    return p


def _latest_scan_summary(results_artifact: dict[str, Any]) -> dict[str, Any]:
    return _first_dict(_dict_list(results_artifact, "scan_results_summary"))


def _ensure_log_grain(logs_artifact: dict[str, Any]) -> dict[str, Any]:
    """Return artifact with selected_toolchains / underlying_errors populated."""
    if "underlying_errors" in logs_artifact and "selected_toolchains" in logs_artifact:
        return logs_artifact
    return enrich_log_artifact(dict(logs_artifact))


def _error_entries(logs_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Legacy message rows (error level only); prefer ``underlying_errors``."""
    out: list[dict[str, Any]] = []
    for message in _dict_list(logs_artifact, "messages"):
        level = dict_str(message, "level")
        payload = as_dict(message.get("json_payload"))
        payload_level = dict_str(payload, "level")
        if level == "LOG_LEVEL_ERROR" or payload_level.lower() == "error":
            out.append(message)
    return out


def _underlying_error_rows(
    logs_artifact: dict[str, Any], *, max_errors: int
) -> list[str]:
    grain = _ensure_log_grain(logs_artifact)
    raw = grain.get("underlying_errors")
    rows: list[dict[str, Any]]
    if isinstance(raw, list) and raw:
        rows = [
            cast("dict[str, Any]", item)
            for item in cast("list[Any]", raw)
            if isinstance(item, dict)
        ]
    else:
        rows = extract_underlying_errors(_dict_list(logs_artifact, "messages"))
    lines: list[str] = []
    for idx, entry in enumerate(rows[:max_errors], start=1):
        ts = dict_str(entry, "timestamp") or "n/a"
        code = dict_str(entry, "code") or "error"
        msg = dict_str(entry, "msg") or "(no msg)"
        details: list[str] = []
        for key in (
            "package_name",
            "command",
            "resolution_error",
            "stderr",
            "caller",
        ):
            value = dict_str(entry, key)
            if value:
                details.append(f"{key}={value}")
        detail_text = "; ".join(details)
        lines.append(
            f"{idx}. **{ts}** `{code}` - {msg}"
            + (f"\n   - {detail_text}" if detail_text else "")
        )
    if len(rows) > max_errors:
        lines.append(
            f"- Note: {len(rows) - max_errors} additional underlying errors omitted "
            f"(max_errors={max_errors})."
        )
    return lines


def _selected_toolchains_block(logs_artifact: dict[str, Any]) -> list[str]:
    grain = _ensure_log_grain(logs_artifact)
    selected = as_dict(grain.get("selected_toolchains"))
    versions = as_dict(selected.get("versions"))
    source = dict_str(selected, "source") or "null"
    detect_fails_raw = selected.get("detect_fails")
    detect_fails: list[str] = []
    if isinstance(detect_fails_raw, list):
        detect_fails = [str(item) for item in cast("list[Any]", detect_fails_raw)]
    lines = [
        "## Selected toolchains (log grain)",
        "",
        f"- source: `{source}`",
    ]
    if versions:
        lines.append("- versions:")
        lines.extend(f"  - `{key}`: `{versions[key]}`" for key in sorted(versions))
    else:
        lines.append(
            "- versions: (none — no `Endorctl toolchains selected` / "
            "`toolchains` field)"
        )
    if detect_fails:
        lines.append("- detect_fails:")
        lines.extend(f"  - `{item}`" for item in detect_fails)
    return lines


def _toolchain_delta_block(
    primary: dict[str, Any], secondary: dict[str, Any] | None
) -> list[str]:
    if secondary is None:
        return []
    prev = as_dict(_ensure_log_grain(secondary).get("selected_toolchains"))
    new = as_dict(_ensure_log_grain(primary).get("selected_toolchains"))
    if not prev and not new:
        prev = extract_selected_toolchains(_dict_list(secondary, "messages"))
        new = extract_selected_toolchains(_dict_list(primary, "messages"))
    delta = diff_selected_toolchain_versions(prev, new)
    lines = [
        "",
        "## Toolchain version delta (pair)",
        "",
        (
            f"- prev_scan_result_uuid: "
            f"`{dict_str(secondary, 'scan_result_uuid') or 'n/a'}`"
        ),
        (f"- new_scan_result_uuid: `{dict_str(primary, 'scan_result_uuid') or 'n/a'}`"),
    ]
    changed = as_dict(delta.get("changed"))
    if changed:
        lines.append("- changed:")
        for key in sorted(changed):
            pair = as_dict(changed.get(key))
            lines.append(f"  - `{key}`: `{pair.get('prev')}` → `{pair.get('new')}`")
    else:
        lines.append("- changed: (none)")
    only_new = as_dict(delta.get("only_new"))
    only_prev = as_dict(delta.get("only_prev"))
    if only_new:
        lines.append("- only_new:")
        lines.extend(f"  - `{k}`: `{only_new[k]}`" for k in sorted(only_new))
    if only_prev:
        lines.append("- only_prev:")
        lines.extend(f"  - `{k}`: `{only_prev[k]}`" for k in sorted(only_prev))
    return lines


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
    """Prefer ``underlying_errors`` full fields over msg-only rows."""
    grain = _ensure_log_grain(logs_artifact)
    underlying_raw = grain.get("underlying_errors")
    entries: list[dict[str, str]] = []
    if isinstance(underlying_raw, list) and underlying_raw:
        for item in cast("list[Any]", underlying_raw):
            if not isinstance(item, dict):
                continue
            row = cast("dict[str, Any]", item)
            parts = [
                f"code={dict_str(row, 'code') or 'n/a'}",
                f"msg={_value_excerpt(row.get('msg') or '', max_len=200)}",
            ]
            for key in (
                "package_name",
                "command",
                "resolution_error",
                "stderr",
                "caller",
            ):
                value = dict_str(row, key)
                if value:
                    parts.append(f"{key}={_value_excerpt(value, max_len=160)}")
            entries.append(
                {
                    "path": "underlying_errors[]",
                    "value": _value_excerpt("; ".join(parts), max_len=400),
                    "source": "scan_logs_artifact",
                }
            )
            if len(entries) >= max_entries:
                break
        return entries

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
    secondary_logs_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scan_raw = _latest_scan_raw(results_artifact, scan_uuid)
    spec = nested_dict(scan_raw, "spec")
    provisioning = nested_dict(spec, "provisioning_result")
    stats = nested_dict(spec, "stats")
    grain = _ensure_log_grain(logs_artifact)
    selected = as_dict(grain.get("selected_toolchains"))
    versions = as_dict(selected.get("versions"))

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
    toolchain_evidence = [
        {
            "path": f"selected_toolchains.versions.{key}",
            "value": str(versions[key]),
            "source": "scan_logs_artifact",
        }
        for key in sorted(versions)
    ]
    toolchain_delta: dict[str, Any] | None = None
    if secondary_logs_artifact is not None:
        prev = as_dict(
            _ensure_log_grain(secondary_logs_artifact).get("selected_toolchains")
        )
        toolchain_delta = diff_selected_toolchain_versions(prev, selected)

    return {
        "tenant": tenant,
        "namespace": namespace,
        "project_uuid": project_uuid,
        "project_name": project_name or None,
        "scan_result_uuid": scan_uuid,
        "selected_toolchains": selected,
        "underlying_errors": grain.get("underlying_errors") or [],
        "toolchain_version_delta": toolchain_delta,
        "status_evidence": status_evidence,
        "provisioning_evidence": provisioning_evidence,
        "stats_evidence": stats_evidence,
        "toolchain_evidence": toolchain_evidence,
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


def _fix_guidance(error_blob: Any) -> list[str]:
    text_blob = json.dumps(error_blob, ensure_ascii=False).lower()
    guidance: list[str] = []

    if (
        "dependency-scanning-error" in text_blob
        or "dependency-resolution-error" in text_blob
    ):
        guidance.append(
            "- Validate dependency manifests first (for example `requirements.txt`, "
            "`pyproject.toml`, lockfiles); cite `resolution_error` / `stderr` / "
            "`command` / `package_name` from underlying_errors — not code tallies "
            "alone."
        )
    if "pypi json api for: python" in text_blob:
        guidance.append(
            "- A `python>=...` requirement appears to be treated as a package lookup; "
            "move interpreter constraints to runtime metadata/config and keep package "
            "dependencies installable."
        )
    if "toolchain-error" in text_blob:
        guidance.append(
            "- Toolchain setup failed in the scan sandbox. Check selected_toolchains "
            "pins, repository/bootstrap steps, and scan worker network/proxy access."
        )
    if "clearsigned file isn't valid" in text_blob or "not signed" in text_blob:
        guidance.append(
            "- Apt repository signature/connectivity error observed; verify network "
            "egress/auth requirements and repository trust chain in scan environment."
        )

    guidance.append(
        "- Compare scan_mode (scan_execution, --quick-scan, --use-local-repo-cache) "
        "and endorctl version against a healthy scan; do not infer GitHub App from "
        "checkout paths."
    )
    guidance.append(
        "- Re-run scan and verify expected deltas (`scan_failures` down, underlying "
        "error fields cleared for affected package paths)."
    )
    return guidance


def _project_name_from_search(search_artifact: dict[str, Any] | None) -> str:
    if search_artifact is None:
        return ""
    projects = _dict_list(search_artifact, "projects")
    if not projects:
        return ""
    return nested_str(projects[0], "meta", "name")


def _scan_mode_markdown_lines(latest: dict[str, Any]) -> list[str]:
    mode_raw = latest.get("scan_mode")
    mode_dict: dict[str, Any] = (
        cast("dict[str, Any]", mode_raw) if isinstance(mode_raw, dict) else {}
    )
    flags_raw = mode_dict.get("endorctl_flags", latest.get("endorctl_flags"))
    flags: list[str] = []
    if isinstance(flags_raw, list):
        flags = [str(item) for item in cast("list[Any]", flags_raw)]
    flag_text = ", ".join(f"`{item}`" for item in flags) if flags else "n/a"
    execution = mode_dict.get("scan_execution", latest.get("scan_execution"))
    run_by_system = mode_dict.get("run_by_system", latest.get("run_by_system"))
    quick_scan = mode_dict.get("quick_scan", latest.get("quick_scan"))
    use_local = mode_dict.get(
        "use_local_repo_cache", latest.get("use_local_repo_cache")
    )
    command = mode_dict.get("command")
    use_scan_profile = mode_dict.get("use_scan_profile")
    python_virtual_env = mode_dict.get("python_virtual_env")
    toolchains_raw: object = (
        mode_dict.get("toolchains") or latest.get("toolchains") or {}
    )
    toolchains: dict[str, Any] = (
        cast("dict[str, Any]", toolchains_raw)
        if isinstance(toolchains_raw, dict)
        else {}
    )
    docker_source = toolchains.get("docker_source")
    return [
        f"- scan_execution: `{execution}`",
        f"- run_by_system: `{run_by_system}`",
        f"- quick_scan: `{quick_scan}`",
        f"- use_local_repo_cache: `{use_local}`",
        f"- use_scan_profile: `{use_scan_profile}`",
        f"- python_virtual_env: `{python_virtual_env}`",
        f"- ToolChainsConfig.DockerSource: `{docker_source}`",
        f"- command: `{command}`",
        f"- endorctl_flags: {flag_text}",
    ]


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
    secondary_logs_path: str | None = None,
    secondary_logs_artifact: dict[str, Any] | None = None,
) -> str:
    latest = _latest_scan_summary(results_artifact)
    grain = _ensure_log_grain(logs_artifact)
    underlying_raw = grain.get("underlying_errors")
    underlying: list[Any] = (
        cast("list[Any]", underlying_raw) if isinstance(underlying_raw, list) else []
    )
    legacy_errors = _error_entries(logs_artifact)

    project_uuid = dict_str(logs_artifact, "project_uuid") or dict_str(
        results_artifact, "project_uuid"
    )
    scan_uuid = dict_str(logs_artifact, "scan_result_uuid") or dict_str(latest, "uuid")
    namespace = dict_str(logs_artifact, "namespace") or dict_str(latest, "namespace")
    project_name = _project_name_from_search(search_artifact)
    project_app_url = dict_str(results_artifact, "project_app_url")
    dual = as_dict(results_artifact.get("dual_scan_pair"))
    profile_refs = as_dict(results_artifact.get("project_profile_refs"))
    discovered = as_dict(latest.get("discovered_manifests"))

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
    ]
    if secondary_logs_path:
        lines.append(f"- secondary_scan_logs (pair baseline): `{secondary_logs_path}`")
    lines.extend(
        [
            "",
            "## Endor app links (cite first)",
            "",
        ]
    )
    if project_app_url:
        lines.append(f"- project: {project_app_url}")
    elif namespace and project_uuid:
        lines.append(
            f"- project: https://app.endorlabs.com/t/{namespace}/projects/{project_uuid}"
        )
    else:
        lines.append("- project: n/a")
    if scan_uuid and namespace:
        lines.append(
            f"- scan-history: https://app.endorlabs.com/t/{namespace}/scan-history/{scan_uuid}"
        )
    analytics_url = dict_str(dual, "analytics_app_url")
    full_sca_url = dict_str(dual, "full_sca_app_url")
    if analytics_url:
        lines.append(f"- latest Analytics: {analytics_url}")
    if full_sca_url:
        lines.append(f"- latest full SCA (TYPE_ALL_SCANS): {full_sca_url}")
    lines.extend(
        [
            "",
            "## Scan Context",
            "",
            f"- tenant: `{tenant}`",
            f"- namespace: `{namespace}`",
            f"- project_uuid: `{project_uuid}`",
            (
                f"- project_name: `{project_name}`"
                if project_name
                else "- project_name: n/a"
            ),
            (
                "- scan_profile_uuid: "
                f"`{dict_str(profile_refs, 'scan_profile_uuid') or None}`"
            ),
            (
                "- toolchain_profile_uuid: "
                f"`{dict_str(profile_refs, 'toolchain_profile_uuid') or None}`"
            ),
            f"- scan_result_uuid: `{scan_uuid}`",
            f"- scan_status: `{dict_str(latest, 'status')}`",
            f"- scan_exit_code: `{dict_str(latest, 'exit_code')}`",
            f"- scan_success: `{dict_str(latest, 'scan_success')}`",
            f"- scan_failures: `{dict_str(latest, 'scan_failures')}`",
            f"- endorctl_version: `{dict_str(latest, 'endorctl_version')}`",
            *_scan_mode_markdown_lines(latest),
            "",
            "## Discovered manifests (embedded logs)",
            "",
            f"- path_count: `{discovered.get('path_count', 0)}`",
            f"- languages: `{discovered.get('languages', [])}`",
            f"- analytics_walk_count: `{discovered.get('analytics_walk_count', 0)}`",
        ]
    )
    paths_raw = discovered.get("paths")
    if isinstance(paths_raw, list) and paths_raw:
        lines.append("- paths:")
        lines.extend(f"  - `{path}`" for path in cast("list[Any]", paths_raw)[:40])
    else:
        lines.append("- paths: (none in embedded logs — pull get_logs including DEBUG)")

    # Prefer underlying errors + toolchain pins above aggregate status commentary.
    lines.extend(["", *_selected_toolchains_block(logs_artifact)])
    lines.extend(_toolchain_delta_block(logs_artifact, secondary_logs_artifact))
    lines.extend(
        [
            "",
            "## Underlying errors (log grain)",
            "",
            (
                "Cite `resolution_error` / `stderr` / `command` / `package_name` — "
                "do not answer ecosystem-degrade questions with status % or "
                "error-code histograms alone."
            ),
            "",
        ]
    )
    underlying_rows = _underlying_error_rows(logs_artifact, max_errors=max_errors)
    if underlying_rows:
        lines.extend(underlying_rows)
    elif legacy_errors:
        lines.append(
            "- No structured underlying_errors; falling back to error-level messages:"
        )
        lines.extend(_error_markdown_rows(legacy_errors, max_errors=max_errors))
    else:
        lines.append("- No underlying error rows detected in scan log artifact.")

    lines.extend(
        [
            "",
            "## What Is Wrong (citing logs)",
            "",
        ]
    )
    if underlying:
        lines.append(
            f"- {len(underlying)} underlying error row(s) extracted "
            "(see **Underlying errors** above)."
        )
        first = underlying[0]
        sample: dict[str, Any] = (
            cast("dict[str, Any]", first) if isinstance(first, dict) else {}
        )
        code = dict_str(sample, "code") or "n/a"
        pkg = dict_str(sample, "package_name") or "n/a"
        lines.append(f"- First row: code=`{code}`, package_name=`{pkg}`.")
    elif legacy_errors:
        lines.extend(_error_markdown_rows(legacy_errors, max_errors=max_errors))
        if len(legacy_errors) > max_errors:
            lines.append(
                f"- Note: {len(legacy_errors) - max_errors} additional error entries "
                f"omitted (max_errors={max_errors})."
            )
    else:
        lines.append("- No error-level log entries detected in scan log artifact.")
    lines.extend(
        [
            "",
            "### Aggregate status (secondary)",
            "",
            f"- scan_status: `{dict_str(latest, 'status')}`",
            f"- scan_success: `{dict_str(latest, 'scan_success')}`",
            f"- scan_failures: `{dict_str(latest, 'scan_failures')}`",
            (
                "- Use status / dependency_count_* only after citing "
                "selected_toolchains and underlying_errors."
            ),
        ]
    )

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
    lines.extend(_fix_guidance(underlying or legacy_errors))
    lines.extend(
        [
            "",
            "## Evidence (Field Paths)",
            "",
            "- toolchain_evidence:",
        ]
    )
    toolchain_lines = _evidence_markdown_lines(evidence_payload, "toolchain_evidence")
    if toolchain_lines:
        lines.extend(toolchain_lines)
    else:
        lines.append("  - (none)")
    lines.append("- status_evidence:")
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
            (
                "- Prefer `selected_toolchains` + `underlying_errors` over status % / "
                "error-code rollups."
            ),
            "- Human review is still required for environment-specific nuances.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    """Run the module CLI and return exit code."""
    args = _build_parser().parse_args()

    results_artifact = _load_json(args.scan_results_artifact)
    logs_artifact = _ensure_log_grain(_load_json(args.scan_logs_artifact))
    secondary_logs_artifact = (
        _ensure_log_grain(_load_json(args.secondary_scan_logs_artifact))
        if args.secondary_scan_logs_artifact
        else None
    )
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
        secondary_logs_artifact=secondary_logs_artifact,
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
        secondary_logs_path=args.secondary_scan_logs_artifact,
        secondary_logs_artifact=secondary_logs_artifact,
    )

    scan_uuid_out = scan_uuid or "unknown-scan"
    root = root_tenant(args.tenant)
    output_dir = resolve_troubleshooting_output_dir(args.tenant, args.output_dir)
    out_path = write_text(
        output_dir=output_dir,
        root_tenant_name=root,
        object_kind="scan_triage",
        object_uuid=scan_uuid_out,
        purpose="summary",
        text=md,
        extension=".md",
        timestamped=args.timestamped,
    )
    evidence_path = write_json(
        output_dir=output_dir,
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
