"""Phase 3 — join inventory + license cache into per-namespace CSV/JSONL."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from endorlabs.context.paths import namespace_path_slug
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.license_export.inventory import load_inventory_jsonl
from endorlabs.workflows.license_export.resolve import (
    load_license_cache,
    load_license_objects,
)
from endorlabs.workflows.license_export.spdx import empty_license_resolution

ExportFormat = Literal["csv", "jsonl"]

JOIN_COLUMNS: tuple[str, ...] = (
    "namespace",
    "project_uuid",
    "project_name",
    "package_name",
    "package_version_uuid",
    "purl",
    "ecosystem",
    "direct",
    "reachable",
    "scope",
    "public",
    "pinned",
    "internal",
    "vendored",
    "last_commit",
    "primary_spdx",
    "all_spdx",
    "source_count",
    "has_declared",
    "has_code",
    "has_package_manager",
)


@dataclass
class JoinResult(WorkflowResult):
    """Outcome of writing a joined dependency+license export file."""

    output_path: str = ""
    row_count: int = 0
    format: str = ""


def join_row(
    inventory_row: dict[str, Any],
    license_row: dict[str, Any] | None,
    *,
    license_object: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge one inventory row with a license cache entry into export columns."""
    lic = license_row or empty_license_resolution()
    row: dict[str, Any] = {
        "namespace": inventory_row.get("namespace", ""),
        "project_uuid": inventory_row.get("project_uuid", ""),
        "project_name": inventory_row.get("project_name", ""),
        "package_name": inventory_row.get("package_name", ""),
        "package_version_uuid": inventory_row.get("package_version_uuid", ""),
        "purl": inventory_row.get("purl", ""),
        "ecosystem": inventory_row.get("ecosystem", ""),
        "direct": bool(inventory_row.get("direct")),
        "reachable": inventory_row.get("reachable", ""),
        "scope": inventory_row.get("scope", ""),
        "public": bool(inventory_row.get("public")),
        "pinned": bool(inventory_row.get("pinned")),
        "internal": bool(inventory_row.get("internal")),
        "vendored": bool(inventory_row.get("vendored")),
        "last_commit": inventory_row.get("last_commit", ""),
        "primary_spdx": lic.get("primary_spdx", ""),
        "all_spdx": lic.get("all_spdx", ""),
        "source_count": int(lic.get("source_count") or 0),
        "has_declared": bool(lic.get("has_declared")),
        "has_code": bool(lic.get("has_code")),
        "has_package_manager": bool(lic.get("has_package_manager")),
    }
    if license_object is not None:
        row["license_object"] = license_object
    return row


def default_join_filename(namespace: str, export_format: ExportFormat) -> str:
    """Filename for the joined per-namespace deliverable."""
    return f"{namespace_path_slug(namespace)}-dep-licenses.{export_format}"


def write_joined_export(
    *,
    inventory_path: str | Path,
    cache_path: str | Path,
    output_path: str | Path,
    export_format: ExportFormat = "csv",
    objects_path: str | Path | None = None,
    include_license_object: bool = False,
) -> JoinResult:
    """Write one joined file from inventory JSONL + license cache JSONL.

    CSV stays flat (customer schema). When *include_license_object* and
    *export_format* is ``jsonl``, attach ``license_object`` from the sidecar
    lookup by ``package_version_uuid``.
    """
    inv_path = Path(inventory_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_inventory_jsonl(inv_path)
    cache = load_license_cache(Path(cache_path))
    objects: dict[str, dict[str, Any]] = {}
    if include_license_object and objects_path is not None:
        objects = load_license_objects(Path(objects_path))

    joined: list[dict[str, Any]] = []
    for row in rows:
        pv = str(row.get("package_version_uuid") or "")
        embed = None
        if include_license_object and export_format == "jsonl":
            obj_row = objects.get(pv)
            if obj_row is not None:
                embed = obj_row.get("license_object", obj_row)
        joined.append(join_row(row, cache.get(pv), license_object=embed))

    if export_format == "jsonl":
        with out_path.open("w", encoding="utf-8") as handle:
            for record in joined:
                handle.write(json.dumps(record, ensure_ascii=False, default=str))
                handle.write("\n")
    else:
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(JOIN_COLUMNS))
            writer.writeheader()
            for record in joined:
                writer.writerow({col: record.get(col, "") for col in JOIN_COLUMNS})

    return JoinResult(
        status="success",
        message=f"Wrote {len(joined)} joined row(s) to {out_path}",
        output_path=str(out_path),
        row_count=len(joined),
        format=export_format,
    )
