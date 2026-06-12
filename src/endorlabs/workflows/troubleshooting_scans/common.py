"""Shared helpers for troubleshooting scan workflows."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from endorlabs.context.paths import workflow_sessions_root
from endorlabs.utils.path_safety import safe_write_text

_DEFAULT_SESSION_USER = "agent"


def default_troubleshooting_output_dir(*, user: str | None = None) -> str:
    """Default RCA/triage directory under workspace/sessions/<user>/troubleshooting/."""
    slug = (user or _DEFAULT_SESSION_USER).strip() or _DEFAULT_SESSION_USER
    return str(workflow_sessions_root(user=slug, subdir="troubleshooting"))


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
        uuid = project.get("uuid", "")
        name = (project.get("meta") or {}).get("name", "")
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
        if project.get("uuid")
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
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    if isinstance(item, dict):
        return item
    return {}


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
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(config.items()):
        if i >= max_keys:
            out["_truncated_keys"] = len(config) - max_keys
            break
        if isinstance(v, dict):
            out[str(k)] = {"kind": "object", "child_keys": list(v.keys())[:40]}
        elif isinstance(v, list):
            out[str(k)] = {"kind": "array", "length": len(v)}
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
    spec = scan_result.get("spec") or {}
    meta = scan_result.get("meta") or {}
    stats = spec.get("stats") or {}
    env = spec.get("environment") or {}
    versions = spec.get("versions") or []
    prov = spec.get("provisioning_result")
    prov_summary: dict[str, Any] | None = None
    if isinstance(prov, dict):
        prov_summary = {
            "provisioning_result_uuid": prov.get("provisioning_result_uuid"),
            "exit_code": prov.get("exit_code"),
            "error": prov.get("error"),
            "tool_chains_source": prov.get("tool_chains_source"),
            "has_scan_profile": bool(prov.get("scan_profile")),
        }
    return {
        **scan_result_metrics(scan_result),
        "meta_parent_uuid": meta.get("parent_uuid"),
        "namespace": (scan_result.get("tenant_meta") or {}).get("namespace"),
        "start_time": spec.get("start_time"),
        "end_time": spec.get("end_time"),
        "duration_seconds": _duration_seconds(
            spec.get("start_time"), spec.get("end_time")
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
            "tools": [
                {"name": t.get("name"), "version": t.get("version")}
                for t in (env.get("tools") or [])
                if isinstance(t, dict)
            ],
            "config_summary": summarize_environment_config(env.get("config")),
        },
        "versions": versions,
        "provisioning_result_summary": prov_summary,
        "log_line_count": len(spec.get("logs") or []),
    }


def duplicate_project_decision(
    matches: Sequence[Any], *, max_auto: int = 3
) -> tuple[bool, list[str], str | None]:
    """Return (proceed_with_all, warnings, error_if_too_many)."""
    n = len(matches)
    if n == 0:
        return False, [], "no_projects_matched"
    if n > max_auto:
        return (
            False,
            [],
            f"too_many_project_matches:{n}>max_auto:{max_auto}",
        )
    warnings: list[str] = []
    if n > 1:
        warnings.append(
            f"duplicate_candidates:{n}:verify_these_are_distinct_projects_before_proceeding"
        )
    return True, warnings, None


def scan_result_metrics(scan_result: dict[str, Any]) -> dict[str, Any]:
    """Extract normalized metrics used for anomaly and diff analysis."""
    spec = scan_result.get("spec") or {}
    stats = spec.get("stats") or {}
    versions = spec.get("versions") or []
    version = versions[0] if versions else {}
    return {
        "uuid": scan_result.get("uuid"),
        "status": spec.get("status"),
        "exit_code": spec.get("exit_code"),
        "create_time": (scan_result.get("meta") or {}).get("create_time"),
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
        "endorctl_version": (spec.get("environment") or {}).get("endorctl_version"),
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
