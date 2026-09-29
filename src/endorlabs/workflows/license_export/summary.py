"""Coverage summary for ``endor-license-export`` runs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

from endorlabs.utils.jsonl_store import load_jsonl_rows
from endorlabs.workflows.license_export.resolve import load_license_cache

EXPORT_SUMMARY_FILENAME = "export_summary.json"


def build_export_summary(
    *,
    namespaces: list[str],
    output_dir: str | Path,
    export_format: str = "",
    workers: int | None = None,
    elapsed_seconds: float | None = None,
    projects_total: int = 0,
    projects_complete: int = 0,
    projects_failed: int = 0,
    inventory_rows: int = 0,
    unique_pvs: int = 0,
    join_rows: int = 0,
    license_consensus: int = 0,
    license_query: int = 0,
    license_missing: int = 0,
    license_with_primary_spdx: int = 0,
    join_paths: list[str] | None = None,
    license_cache_path: str = "",
    license_objects_path: str = "",
    status: str = "success",
    message: str = "",
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build a portable export_summary.json payload (no estate literals required)."""
    return {
        "status": status,
        "message": message,
        "errors": list(errors or []),
        "namespaces": list(namespaces),
        "workers": workers,
        "elapsed_seconds": (
            round(elapsed_seconds, 3) if elapsed_seconds is not None else None
        ),
        "format": export_format,
        "projects": {
            "total": projects_total,
            "complete": projects_complete,
            "failed": projects_failed,
        },
        "inventory_rows": inventory_rows,
        "unique_package_versions": unique_pvs,
        "join_rows": join_rows,
        "license": {
            "consensus": license_consensus,
            "query": license_query,
            "missing": license_missing,
            "with_primary_spdx": license_with_primary_spdx,
        },
        "paths": {
            "output_dir": str(output_dir),
            "join_files": list(join_paths or []),
            "license_cache": license_cache_path,
            "license_objects": license_objects_path,
            "summary": str(Path(output_dir) / EXPORT_SUMMARY_FILENAME),
        },
    }


def summarize_license_cache(cache_path: Path) -> dict[str, int]:
    """Count resolution outcomes from a license_cache.jsonl file."""
    cache = load_license_cache(cache_path)
    query = 0
    missing = 0
    with_spdx = 0
    for row in cache.values():
        resolution = str(row.get("resolution") or "")
        if resolution == "package_license_query":
            query += 1
        if row.get("primary_spdx"):
            with_spdx += 1
        else:
            missing += 1
    return {
        "consensus": 0,
        "query": query,
        "missing": missing,
        "with_primary_spdx": with_spdx,
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
    license_obj: Any = summary.get("license")
    license_block: dict[str, Any] = (
        cast("dict[str, Any]", license_obj) if isinstance(license_obj, dict) else {}
    )
    elapsed = summary.get("elapsed_seconds")
    elapsed_s = f"{elapsed}s" if elapsed is not None else "n/a"
    return (
        f"export_summary: status={summary.get('status')} "
        f"ns={len(summary.get('namespaces') or [])} "
        f"workers={summary.get('workers')} elapsed={elapsed_s} "
        f"projects={projects.get('complete', 0)}/{projects.get('total', 0)} "
        f"(failed={projects.get('failed', 0)}) "
        f"inventory_rows={summary.get('inventory_rows', 0)} "
        f"unique_pvs={summary.get('unique_package_versions', 0)} "
        f"join_rows={summary.get('join_rows', 0)} "
        f"license_spdx={license_block.get('with_primary_spdx', 0)} "
        f"(consensus={license_block.get('consensus', 0)}, "
        f"query={license_block.get('query', 0)}, "
        f"missing={license_block.get('missing', 0)})"
    )


def inventory_rows_from_path(path: Path) -> list[dict[str, Any]]:
    """Load inventory rows (alias for callers that already import summary)."""
    return load_jsonl_rows(path)


class ElapsedTimer:
    """Simple wall-clock timer for pipeline summaries."""

    def __init__(self) -> None:
        super().__init__()
        self._start = time.perf_counter()

    def elapsed(self) -> float:
        """Seconds since this timer was created."""
        return time.perf_counter() - self._start
