"""SBOM / VEX export via Client facades (and optional AsyncJob poll)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from endorlabs.workflows.common import WorkflowResult

_TERMINAL = frozenset(
    {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED",
    }
)


@dataclass
class ExportResult(WorkflowResult):
    """Result of an SBOMExport / VEXExport create (sync or async)."""

    kind: str = "sbom"  # sbom | vex
    export_uuid: str | None = None
    async_job_uuid: str | None = None
    data: str | None = None
    output_format: str | None = None
    component_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for CLI artifacts."""
        return {
            "status": self.status,
            "message": self.message,
            "errors": list(self.errors),
            "kind": self.kind,
            "export_uuid": self.export_uuid,
            "async_job_uuid": self.async_job_uuid,
            "format": self.output_format,
            "component_type": self.component_type,
            "data_len": len(self.data) if self.data else 0,
        }


def _unwrap(value: Any) -> Any:
    return getattr(value, "value", value)


def run_sbom_export(
    client: Any,
    *,
    parent_kind: str,
    parent_uuid: str,
    component_type: str = "COMPONENT_TYPE_APPLICATION",
    kind: str = "SBOM_KIND_CYCLONEDX",
    output_format: str = "FORMAT_JSON",
    name: str = "sbom-export",
    include_test_dependencies: bool = False,
) -> ExportResult:
    """Create an SBOM export (``client.SBOMExport.create``).

    ``meta.parent_kind`` is ``PackageVersion`` or ``RepositoryVersion``.
    Sync responses may include ``spec.data``; large/async exports may return
    without data — use :func:`poll_async_job` when a job UUID is available.
    """
    try:
        result = client.SBOMExport.create(
            meta={
                "name": name,
                "parent_kind": parent_kind,
                "parent_uuid": parent_uuid,
            },
            spec={
                "component_type": component_type,
                "kind": kind,
                "format": output_format,
                "include_test_dependencies": include_test_dependencies,
            },
        )
    except Exception as exc:
        return ExportResult(
            status="error",
            message=f"SBOMExport.create failed: {exc}",
            errors=[str(exc)],
            kind="sbom",
            output_format=output_format,
            component_type=component_type,
        )

    data = _unwrap(getattr(getattr(result, "spec", None), "data", None))
    uuid = _unwrap(getattr(result, "uuid", None))
    return ExportResult(
        status="success",
        message=f"SBOMExport created uuid={uuid}",
        kind="sbom",
        export_uuid=str(uuid) if uuid else None,
        data=str(data) if data else None,
        output_format=output_format,
        component_type=component_type,
    )


def run_vex_export(
    client: Any,
    *,
    parent_kind: str,
    parent_uuid: str,
    component_type: str = "COMPONENT_TYPE_APPLICATION",
    output_format: str = "FORMAT_JSON",
    name: str = "vex-export",
) -> ExportResult:
    """Create a VEX export (``client.VEXExport.create``)."""
    try:
        result = client.VEXExport.create(
            meta={
                "name": name,
                "parent_kind": parent_kind,
                "parent_uuid": parent_uuid,
            },
            spec={
                "component_type": component_type,
                "format": output_format,
            },
        )
    except Exception as exc:
        return ExportResult(
            status="error",
            message=f"VEXExport.create failed: {exc}",
            errors=[str(exc)],
            kind="vex",
            output_format=output_format,
            component_type=component_type,
        )

    data = _unwrap(getattr(getattr(result, "spec", None), "data", None))
    uuid = _unwrap(getattr(result, "uuid", None))
    return ExportResult(
        status="success",
        message=f"VEXExport created uuid={uuid}",
        kind="vex",
        export_uuid=str(uuid) if uuid else None,
        data=str(data) if data else None,
        output_format=output_format,
        component_type=component_type,
    )


def poll_async_job(
    client: Any,
    job_uuid: str,
    *,
    timeout_s: float = 120.0,
    interval_s: float = 2.0,
) -> Any:
    """Poll ``client.AsyncJob.get`` until a terminal state or timeout.

    Returns the last AsyncJob resource. Raises ``TimeoutError`` on timeout.
    """
    deadline = time.monotonic() + timeout_s
    last: Any = None
    while time.monotonic() < deadline:
        last = client.AsyncJob.get(job_uuid)
        state = str(_unwrap(getattr(getattr(last, "spec", None), "state", None)) or "")
        if state in _TERMINAL:
            return last
        time.sleep(interval_s)
    raise TimeoutError(f"AsyncJob {job_uuid} not terminal within {timeout_s}s")
