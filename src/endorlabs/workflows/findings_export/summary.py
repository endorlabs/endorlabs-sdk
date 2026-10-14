"""Coverage summary for ``endor-findings-export`` runs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

EXPORT_SUMMARY_FILENAME = "export_summary.json"


def build_export_summary(
    *,
    namespaces: list[str],
    output_dir: str | Path,
    workers: int | None = None,
    elapsed_seconds: float | None = None,
    projects_total: int = 0,
    projects_complete: int = 0,
    projects_failed: int = 0,
    finding_rows: int = 0,
    mask: str | None = None,
    status: str = "success",
    message: str = "",
    errors: list[str] | None = None,
    namespace_paths: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build a portable export_summary.json payload (placeholders only in docs)."""
    return {
        "status": status,
        "message": message,
        "errors": list(errors or []),
        "namespaces": list(namespaces),
        "workers": workers,
        "elapsed_seconds": (
            round(elapsed_seconds, 3) if elapsed_seconds is not None else None
        ),
        "format": "jsonl",
        "mask": mask or "",
        "projects": {
            "total": projects_total,
            "complete": projects_complete,
            "failed": projects_failed,
        },
        "finding_rows": finding_rows,
        "paths": {
            "output_dir": str(output_dir),
            "namespaces": list(namespace_paths or []),
            "summary": str(Path(output_dir) / EXPORT_SUMMARY_FILENAME),
        },
    }


def write_export_summary(output_dir: Path | str, summary: dict[str, Any]) -> Path:
    """Write ``export_summary.json`` under *output_dir*; return the path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / EXPORT_SUMMARY_FILENAME
    path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    return path


def format_summary_line(summary: dict[str, Any]) -> str:
    """One-line human summary for stdout/stderr."""
    projects_obj: Any = summary.get("projects")
    projects: dict[str, Any] = (
        cast("dict[str, Any]", projects_obj) if isinstance(projects_obj, dict) else {}
    )
    elapsed = summary.get("elapsed_seconds")
    elapsed_s = f"{elapsed}s" if elapsed is not None else "n/a"
    return (
        f"export_summary: status={summary.get('status')} "
        f"ns={len(summary.get('namespaces') or [])} "
        f"workers={summary.get('workers')} elapsed={elapsed_s} "
        f"projects={projects.get('complete', 0)}/{projects.get('total', 0)} "
        f"(failed={projects.get('failed', 0)}) "
        f"finding_rows={summary.get('finding_rows', 0)}"
    )


class ElapsedTimer:
    """Simple wall-clock timer for pipeline summaries."""

    def __init__(self) -> None:
        super().__init__()
        self._start = time.perf_counter()

    def elapsed(self) -> float:
        """Seconds since this timer was created."""
        return time.perf_counter() - self._start
