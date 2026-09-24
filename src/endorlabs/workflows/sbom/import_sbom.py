"""Import SBOM via ``endorctl sbom import`` (ingest + scan)."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.sbom.coverage import CoverageResult, run_coverage

_PROJECT_UUID_RE = re.compile(
    r"Scanning Project UUID:\s*([0-9a-fA-F]{24})"
    r"|SBOM import complete for project:\s*'([0-9a-fA-F]{24})'",
)
_SBOM_NAME_RE = re.compile(r"SBOM name:\s*'([^']+)'")


@dataclass
class ImportResult(WorkflowResult):
    """Result of an ``endorctl sbom import`` run."""

    namespace: str = ""
    sbom_path: str = ""
    project_uuid: str | None = None
    sbom_name: str | None = None
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    coverage: CoverageResult | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for CLI artifacts."""
        cov = self.coverage.to_dict() if self.coverage is not None else None
        return {
            "status": self.status,
            "message": self.message,
            "errors": list(self.errors),
            "namespace": self.namespace,
            "sbom_path": self.sbom_path,
            "project_uuid": self.project_uuid,
            "sbom_name": self.sbom_name,
            "returncode": self.returncode,
            "coverage": cov,
        }


def resolve_endorctl() -> str | None:
    """Return path to ``endorctl`` / ``endorctl.exe`` on PATH, or None."""
    return shutil.which("endorctl") or shutil.which("endorctl.exe")


def _detect_format(path: Path, format_hint: str | None) -> str | None:
    if format_hint:
        return format_hint.lower().strip() or None
    # SPDX needs --format=spdx; CycloneDX is the default.
    if path.suffix.lower() == ".json":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            return None
        if '"spdxVersion"' in text or '"SPDXID"' in text:
            return "spdx"
    return None


def parse_import_output(combined: str) -> tuple[str | None, str | None]:
    """Extract project UUID and SBOM name from endorctl import logs."""
    project_uuid: str | None = None
    for match in _PROJECT_UUID_RE.finditer(combined):
        project_uuid = match.group(1) or match.group(2)
    sbom_name: str | None = None
    name_match = _SBOM_NAME_RE.search(combined)
    if name_match:
        sbom_name = name_match.group(1)
    return project_uuid, sbom_name


def run_import(
    *,
    namespace: str,
    sbom_path: Path,
    sbom_format: str | None = None,
    endorctl: str | None = None,
    client: Any | None = None,
    run_coverage_after: bool = False,
    timeout_s: int = 600,
) -> ImportResult:
    """Run ``endorctl sbom import`` and optionally post-import coverage.

    Prefer this path over API ``ImportedSBOM.create`` when an immediate scan is
    required — ingest+scan runs inside endorctl, not as a side effect of API create.
    """
    path = Path(sbom_path)
    if not path.is_file():
        return ImportResult(
            status="error",
            message=f"SBOM file not found: {path}",
            errors=[f"missing file: {path}"],
            namespace=namespace,
            sbom_path=str(path),
        )

    exe = endorctl or resolve_endorctl()
    if not exe:
        return ImportResult(
            status="error",
            message="endorctl not found on PATH",
            errors=["endorctl missing"],
            namespace=namespace,
            sbom_path=str(path),
        )

    fmt = _detect_format(path, sbom_format)
    cmd = [
        exe,
        "sbom",
        "import",
        "-n",
        namespace,
        f"--sbom-file-path={path}",
    ]
    if fmt == "spdx":
        cmd.append("--format=spdx")

    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ImportResult(
            status="error",
            message=f"endorctl sbom import failed to start: {exc}",
            errors=[str(exc)],
            namespace=namespace,
            sbom_path=str(path),
        )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    project_uuid, sbom_name = parse_import_output(combined)
    if proc.returncode != 0:
        return ImportResult(
            status="error",
            message=f"endorctl sbom import exited {proc.returncode}",
            errors=[combined.strip()[-2000:] or f"exit {proc.returncode}"],
            namespace=namespace,
            sbom_path=str(path),
            project_uuid=project_uuid,
            sbom_name=sbom_name,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )

    coverage: CoverageResult | None = None
    if run_coverage_after and client is not None and project_uuid:
        coverage = run_coverage(client, sbom_path=path, project_uuid=project_uuid)

    status = "success"
    message = f"Imported SBOM project={project_uuid} name={sbom_name}"
    if coverage is not None and coverage.status != "success":
        status = "partial"
        message = f"{message}; coverage={coverage.message}"

    return ImportResult(
        status=status,
        message=message,
        errors=[],
        namespace=namespace,
        sbom_path=str(path),
        project_uuid=project_uuid,
        sbom_name=sbom_name,
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        coverage=coverage,
    )
