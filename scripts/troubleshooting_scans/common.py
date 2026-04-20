"""Shared helpers for troubleshooting scan workflows."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client


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
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / build_filename(
        root_tenant_name=root_tenant_name,
        object_kind=object_kind,
        object_uuid=object_uuid,
        purpose=purpose,
        extension=".json",
        timestamped=timestamped,
    )
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
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
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / build_filename(
        root_tenant_name=root_tenant_name,
        object_kind=object_kind,
        object_uuid=object_uuid,
        purpose=purpose,
        extension=extension,
        timestamped=timestamped,
    )
    path.write_text(text, encoding="utf-8")
    return path


def build_api_client() -> APIClient:
    """Construct API client from environment variables."""
    return APIClient()


def build_scanlogs_client(tenant: str) -> Client:
    """Construct high-level client for ScanLogs facade."""
    return Client(tenant=tenant)


def list_projects(
    api: APIClient, namespace: str, traverse: bool | None = None
) -> list[dict[str, Any]]:
    """List projects under a namespace.

    Default behavior is namespace-aware:
    - Root tenant namespace (no dot): traverse=true for discovery across children.
    - Child namespace (contains dot): traverse=false for direct namespace listing.
    """
    if traverse is None:
        traverse = "." not in namespace
    params = {"list_parameters.traverse": str(traverse).lower()}
    return list(api.get_all(f"v1/namespaces/{namespace}/projects", params=params))


def match_projects(
    projects: list[dict[str, Any]],
    *,
    project_uuid: str | None,
    project_name: str | None,
    project_url: str | None,
    project_name_regex: str | None,
) -> list[dict[str, Any]]:
    """Apply project selection filters."""
    regex = re.compile(project_name_regex, re.IGNORECASE) if project_name_regex else None
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


def list_scan_results_for_project(
    api: APIClient,
    *,
    namespace: str,
    project_uuid: str,
    limit: int,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """List and locally filter scan results for a project."""
    params = {
        "list_parameters.traverse": "false",
        "list_parameters.sort_path": "meta.create_time",
        "list_parameters.sort_order": "descending",
    }
    results = list(api.get_all(f"v1/namespaces/{namespace}/scan-results", params=params))
    filtered = [
        item
        for item in results
        if (item.get("meta") or {}).get("parent_uuid") == project_uuid
    ]
    if status_filter:
        filtered = [
            item
            for item in filtered
            if (item.get("spec") or {}).get("status") == status_filter
        ]
    return filtered[:limit]


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
        default=".tmp",
        help="Directory for generated artifacts (default: .tmp)",
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
