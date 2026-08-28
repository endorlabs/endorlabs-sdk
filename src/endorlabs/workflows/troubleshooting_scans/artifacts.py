"""Filename contract and artifact writers for troubleshooting scan workflows."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endorlabs.context.paths import flat_task_dir, task_activity_dir
from endorlabs.utils.artifact_io import write_json as write_json_file
from endorlabs.utils.path_safety import safe_write_text

RUN_BUCKET = "troubleshooting"


def resolve_troubleshooting_output_dir(
    namespace: str | None,
    output_dir: str | Path | None = None,
) -> Path:
    """Resolve RCA output directory under ``tasks/<slug>-<date>/troubleshooting/``."""
    if output_dir:
        return Path(output_dir)
    if namespace and str(namespace).strip():
        return task_activity_dir(str(namespace).strip(), RUN_BUCKET)
    return flat_task_dir(RUN_BUCKET)


def default_troubleshooting_output_dir(
    namespace: str | None = None,
    *,
    user: str | None = None,
) -> str:
    """Default RCA directory (requires namespace for tenant-day bucket)."""
    _ = user
    return str(resolve_troubleshooting_output_dir(namespace))


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
    write_json_file(path, payload, base_dir=output_dir)
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
