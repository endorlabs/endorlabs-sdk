"""Shared helpers for troubleshooting scan workflows."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from endorlabs.context.paths import default_runs_dir
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.wire_access import (
    dict_str,
    model_to_dict,
    nested_dict,
    nested_str,
)

RUN_BUCKET = "troubleshooting-scans"


def default_troubleshooting_output_dir(*, user: str | None = None) -> str:
    """Default RCA/triage directory under ``workspace/runs/troubleshooting-scans/``."""
    _ = user  # legacy param; user slug no longer in path
    return str(default_runs_dir(RUN_BUCKET))


def iso_now_compact() -> str:
    """Return current UTC timestamp suitable for filenames."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def sanitize_segment(value: str) -> str:
    """Normalize a filename segment to ASCII-safe token characters."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-._") or "unknown"


def root_tenant(namespace: str) -> str:
    """Return root tenant from a namespace like tenant.child.sub."""
    return namespace.split(".", maxsplit=1)[0]


def build_filename(
    *,
    root_tenant_name: str,
    object_kind: str,
    object_uuid: str,
    purpose: str,
    extension: str,
    timestamped: bool = False,
) -> str:
    """Build a contract-compliant filename.

    Required segments:
      {rootTenant}__{objectKind}__{objectUuid}
    Optional segments:
      __{purpose} and __{timestamp}
    """
    parts = [
        sanitize_segment(root_tenant_name),
        sanitize_segment(object_kind),
        sanitize_segment(object_uuid),
        sanitize_segment(purpose),
    ]
    if timestamped:
        parts.append(iso_now_compact())
    ext = extension if extension.startswith(".") else f".{extension}"
    return "__".join(parts) + ext


def write_json(
    *,
    output_dir: Path,
    root_tenant_name: str,
    object_kind: str,
    object_uuid: str,
    purpose: str,
    payload: Any,
    timestamped: bool = False,
) -> Path:
    """Write JSON payload using filename contract."""
    path = output_dir / build_filename(
        root_tenant_name=root_tenant_name,
        object_kind=object_kind,
        object_uuid=object_uuid,
        purpose=purpose,
        extension=".json",
        timestamped=timestamped,
    )
    safe_write_text(output_dir, path, json.dumps(payload, indent=2))
    return path


def write_text(
    *,
    output_dir: Path,
    root_tenant_name: str,
    object_kind: str,
    object_uuid: str,
    purpose: str,
    text: str,
    extension: str,
    timestamped: bool = False,
) -> Path:
    """Write text payload using filename contract."""
    path = output_dir / build_filename(
        root_tenant_name=root_tenant_name,
        object_kind=object_kind,
        object_uuid=object_uuid,
        purpose=purpose,
        extension=extension,
        timestamped=timestamped,
    )
    safe_write_text(output_dir, path, text)
    return path


def match_projects(
    projects: list[dict[str, Any]],
    *,
    project_uuid: str | None,
    project_name: str | None,
    project_url: str | None,
    project_name_regex: str | None,
) -> list[dict[str, Any]]:
    """Apply project selection filters."""
    regex = (
        re.compile(project_name_regex, re.IGNORECASE) if project_name_regex else None
    )
    selected: list[dict[str, Any]] = []
    for project in projects:
        uuid = dict_str(project, "uuid")
        name = nested_str(project, "meta", "name")
        if project_uuid and uuid != project_uuid:
            continue
        if project_name and project_name.lower() not in str(name).lower():
            continue
        if project_url and project_url.lower() not in str(name).lower():
            continue
        if regex and not regex.search(str(name)):
            continue
        selected.append(project)
    return selected


def parallel_collect_for_projects(
    projects: Sequence[dict[str, Any]],
    fetch_fn: Callable[[Any], Iterable[Any]],
    *,
    max_workers: int,
    fallback_ns: str,
    progress_label: str,
    progress_every: int = 50,
) -> list[Any]:
    """Parallel per-project fetch; flatten iterable results from each shard."""
    from endorlabs.tools.list_sharding import (
        parallel_map_shards,
        project_dict_to_shard,
    )

    shards = [
        project_dict_to_shard(project, fallback_ns)
        for project in projects
        if dict_str(project, "uuid")
    ]
    per_shard = parallel_map_shards(
        shards,
        fetch_fn,
        max_workers=max_workers,
        progress_label=progress_label,
        progress_every=progress_every,
    )
    out: list[Any] = []
    for batch in per_shard:
        out.extend(batch)
    return out


def object_to_dict(item: Any) -> dict[str, Any]:
    """Convert SDK model objects to JSON dict; passthrough dicts."""
    return model_to_dict(item)


def project_namespace(project: Any) -> str | None:
    """Extract tenant namespace from project-like object."""
    tenant_meta = getattr(project, "tenant_meta", None)
    ns = getattr(tenant_meta, "namespace", None)
    return str(ns) if ns else None


def scanlog_line(message: Any) -> str:
    """Normalize a scan log message object into plain text."""
    level = str(getattr(message, "log_level", "UNKNOWN"))
    timestamp = getattr(message, "timestamp", "")
    text = getattr(message, "message", "")
    return f"{timestamp} [{level}] {text}"


def scanlog_line_has_content(line: str) -> bool:
    """Return whether a normalized or embedded scan log line carries message text."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return True
        if not isinstance(payload, dict):
            return True
        payload_dict = cast("dict[str, Any]", payload)
        msg = dict_str(payload_dict, "msg") or dict_str(payload_dict, "message")
        return bool(msg.strip())
    if "]" in stripped:
        return bool(stripped.rsplit("]", 1)[-1].strip())
    return True


def scanlog_entries_have_content(entries: Sequence[str]) -> bool:
    """Return whether any scan log line includes non-empty message text."""
    return any(scanlog_line_has_content(line) for line in entries)


# App UI: https://app.endorlabs.com/t/{namespace}/scan-history/{scan_result_uuid}
_APP_SCAN_HISTORY_URL = re.compile(
    r"^https://app\.endorlabs\.com/t/(?P<ns>[^/]+)/scan-history/(?P<uuid>[0-9a-f]{24})(?:[/?#].*)?$",
    re.IGNORECASE,
)
# Findings, versions, etc.: .../t/{namespace}/projects/{project_uuid}/...
_APP_PROJECT_URL = re.compile(
    r"^https://app\.endorlabs\.com/t/(?P<ns>[^/]+)/projects/(?P<puuid>[0-9a-f]{24})(?:/.*)?(?:[?#].*)?$",
    re.IGNORECASE,
)


def parse_app_scan_history_url(url: str) -> tuple[str, str]:
    """Parse namespace and ScanResult UUID from an Endor Labs app scan-history URL."""
    m = _APP_SCAN_HISTORY_URL.match(url.strip())
    if not m:
        raise ValueError(
            "URL must look like "
            "https://app.endorlabs.com/t/{namespace}/scan-history/{scan_result_uuid}"
        )
    return m.group("ns"), m.group("uuid")


def parse_endor_app_url(url: str) -> dict[str, str]:
    """Classify app.endorlabs.com URLs; extract fields for troubleshooting scripts.

    Routing only: pass ``--tenant`` separately (same as SDK / env). This parser does
    not infer tenant from the URL.

    Returns:
        - ``kind`` — ``"scan_history"`` or ``"project"``.
        - ``namespace`` — path segment after ``/t/`` (e.g. ``a.b.c``).
        - ``scan_result_uuid`` or ``project_uuid`` depending on ``kind``.
    """
    raw = url.strip()
    m_hist = _APP_SCAN_HISTORY_URL.match(raw)
    if m_hist:
        ns = m_hist.group("ns")
        return {
            "kind": "scan_history",
            "namespace": ns,
            "scan_result_uuid": m_hist.group("uuid"),
        }
    m_proj = _APP_PROJECT_URL.match(raw)
    if m_proj:
        ns = m_proj.group("ns")
        return {
            "kind": "project",
            "namespace": ns,
            "project_uuid": m_proj.group("puuid"),
        }
    raise ValueError(
        "Unrecognized app URL. Expected scan-history: "
        "https://app.endorlabs.com/t/{namespace}/scan-history/{scan_result_uuid} "
        "or project: https://app.endorlabs.com/t/{namespace}/projects/{project_uuid}/..."
    )


def date_window_from_days(*, days: int, end: datetime | None = None) -> tuple[str, str]:
    """Return (from_date, to_date) ISO strings for ListParameters, inclusive window."""
    if days < 0:
        raise ValueError("days must be non-negative")
    end_dt = (end or datetime.now(UTC)).astimezone(UTC)
    start_dt = end_dt - timedelta(days=days)
    return _dt_iso_z(start_dt), _dt_iso_z(end_dt)


def date_window_from_bounds(
    *,
    from_date: str | None,
    to_date: str | None,
    days: int | None,
    end: datetime | None = None,
) -> tuple[str, str]:
    """Resolve list window: explicit from/to wins; else last ``days`` (default 7)."""
    if from_date and to_date:
        return from_date, to_date
    if from_date or to_date:
        raise ValueError("Provide both --from-date and --to-date, or neither")
    d = days if days is not None else 7
    return date_window_from_days(days=d, end=end)


def _dt_iso_z(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def summarize_environment_config(config: Any, *, max_keys: int = 80) -> dict[str, Any]:
    """Shape-only summary of spec.environment.config (no secret values)."""
    if not isinstance(config, dict):
        return {}
    config_dict = cast("dict[str, Any]", config)
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(config_dict.items()):
        if i >= max_keys:
            out["_truncated_keys"] = len(config_dict) - max_keys
            break
        if isinstance(v, dict):
            v_dict = cast("dict[str, Any]", v)
            out[str(k)] = {"kind": "object", "child_keys": list(v_dict.keys())[:40]}
        elif isinstance(v, list):
            out[str(k)] = {"kind": "array", "length": len(cast("list[Any]", v))}
        else:
            out[str(k)] = {"kind": "scalar"}
    return out


def _duration_seconds(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    try:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end)
        return (e - s).total_seconds()
    except (TypeError, ValueError):
        return None


def scan_result_extended_summary(scan_result: dict[str, Any]) -> dict[str, Any]:
    """Rich machine-readable summary for ScanResult triage (dict/API shape)."""
    spec = nested_dict(scan_result, "spec")
    meta = nested_dict(scan_result, "meta")
    stats = nested_dict(spec, "stats")
    env = nested_dict(spec, "environment")
    versions_raw = spec.get("versions")
    versions: list[Any] = (
        cast("list[Any]", versions_raw) if isinstance(versions_raw, list) else []
    )
    prov = spec.get("provisioning_result")
    prov_summary: dict[str, Any] | None = None
    if isinstance(prov, dict):
        prov_dict = cast("dict[str, Any]", prov)
        prov_summary = {
            "provisioning_result_uuid": prov_dict.get("provisioning_result_uuid"),
            "exit_code": prov_dict.get("exit_code"),
            "error": prov_dict.get("error"),
            "tool_chains_source": prov_dict.get("tool_chains_source"),
            "has_scan_profile": bool(prov_dict.get("scan_profile")),
        }
    tools_raw = env.get("tools")
    tools: list[dict[str, Any]] = []
    if isinstance(tools_raw, list):
        for raw_tool in cast("list[Any]", tools_raw):
            if not isinstance(raw_tool, dict):
                continue
            tool_dict = cast("dict[str, Any]", raw_tool)
            tools.append(
                {
                    "name": tool_dict.get("name"),
                    "version": tool_dict.get("version"),
                }
            )
    logs_raw = spec.get("logs")
    log_line_count = (
        len(cast("list[Any]", logs_raw)) if isinstance(logs_raw, list) else 0
    )
    return {
        **scan_result_metrics(scan_result),
        "meta_parent_uuid": meta.get("parent_uuid"),
        "namespace": nested_str(scan_result, "tenant_meta", "namespace"),
        "start_time": spec.get("start_time"),
        "end_time": spec.get("end_time"),
        "duration_seconds": _duration_seconds(
            dict_str(spec, "start_time") or None,
            dict_str(spec, "end_time") or None,
        ),
        "type": spec.get("type"),
        "has_panic": spec.get("has_panic"),
        "languages_detected": spec.get("languages_detected"),
        "runtimes_ms": spec.get("runtimes"),
        "ecosystem_dep_counts": spec.get("ecosystem_dep_counts"),
        "ecosystem_pkg_counts": spec.get("ecosystem_pkg_counts"),
        "stats": stats,
        "environment": {
            "arch": env.get("arch"),
            "os": env.get("os"),
            "num_cpus": env.get("num_cpus"),
            "memory_bytes": env.get("memory"),
            "endorctl_version": env.get("endorctl_version"),
            "tools": tools,
            "config_summary": summarize_environment_config(env.get("config")),
        },
        "versions": versions,
        "provisioning_result_summary": prov_summary,
        "log_line_count": log_line_count,
    }


def scan_result_metrics(scan_result: dict[str, Any]) -> dict[str, Any]:
    """Extract normalized metrics used for anomaly and diff analysis."""
    spec = nested_dict(scan_result, "spec")
    stats = nested_dict(spec, "stats")
    versions_raw = spec.get("versions")
    versions: list[Any] = (
        cast("list[Any]", versions_raw) if isinstance(versions_raw, list) else []
    )
    version = cast("dict[str, Any]", versions[0]) if versions else {}
    if versions and not isinstance(versions[0], dict):
        version = {}
    return {
        "uuid": scan_result.get("uuid"),
        "status": spec.get("status"),
        "exit_code": spec.get("exit_code"),
        "create_time": nested_str(scan_result, "meta", "create_time"),
        "scan_success": stats.get("scan_success", 0),
        "scan_failures": stats.get("scan_failures", 0),
        "findings_critical": stats.get("findings_critical", 0),
        "findings_high": stats.get("findings_high", 0),
        "findings_medium": stats.get("findings_medium", 0),
        "findings_low": stats.get("findings_low", 0),
        "dependency_analysis_num_full": stats.get("dependency_analysis_num_full", 0),
        "dependency_analysis_num_approximate": stats.get(
            "dependency_analysis_num_approximate", 0
        ),
        "dependency_count_total": stats.get("dependency_count_total", 0),
        "endorctl_version": nested_str(spec, "environment", "endorctl_version"),
        "sha": version.get("sha"),
        "ref": version.get("ref"),
    }


def load_json(path: str | Path) -> Any:
    """Load JSON file from path string or Path."""
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


def parse_common_args(description: str) -> argparse.ArgumentParser:
    """Build parser with common options used by all scripts."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--tenant", required=True, help="Target namespace/tenant root")
    parser.add_argument(
        "--output-dir",
        default=default_troubleshooting_output_dir(),
        help=(
            "Directory for generated artifacts "
            f"(default: {default_troubleshooting_output_dir()})"
        ),
    )
    parser.add_argument(
        "--timestamped",
        action="store_true",
        help="Append timestamp suffix to output filenames",
    )
    parser.add_argument(
        "--strict-filename-contract",
        action="store_true",
        default=True,
        help="Enforce rootTenant__objectKind__objectUuid naming (default: true)",
    )
    return parser
