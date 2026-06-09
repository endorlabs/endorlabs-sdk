"""DependencyMetadata workspace helpers."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from endorlabs.workflows.estate.contracts import RESOURCE_DEPENDENCY_METADATA
from endorlabs.workflows.estate.workspace.paths import resource_path


def load_dependency_metadata_records(workspace_root: Path) -> list[dict[str, Any]]:
    """Load DependencyMetadata rows from ``data/dependency_metadata.jsonl``."""
    path = resource_path(workspace_root, RESOURCE_DEPENDENCY_METADATA)
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def dep_data_from_record(record: dict[str, Any]) -> dict[str, Any]:
    row = record.get("row") or {}
    raw_spec = row.get("spec")
    spec: dict[str, Any] = raw_spec if isinstance(raw_spec, dict) else {}
    raw_dep = spec.get("dependency_data")
    return raw_dep if isinstance(raw_dep, dict) else {}


def dependency_metadata_record_from_row(
    row: Any, *, project_uuid: str
) -> dict[str, Any]:
    if isinstance(row, dict):
        payload: dict[str, Any] = row
    else:
        spec = getattr(row, "spec", None)
        if hasattr(row, "model_dump"):
            payload = row.model_dump(mode="json", warnings=False)
        elif spec is not None and hasattr(spec, "model_dump"):
            payload = {"spec": spec.model_dump(mode="json", warnings=False)}
        else:
            payload = {"spec": {}}
    return {
        "project_uuid": project_uuid,
        "dm_uuid": payload.get("uuid"),
        "row": payload,
    }


def aggregate_usage_by_package_version(
    records: list[dict[str, Any]],
    package_name: str,
) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for record in records:
        dep = dep_data_from_record(record)
        name = str(dep.get("package_name") or "")
        if name != package_name:
            continue
        version = str(
            dep.get("resolved_version") or dep.get("unresolved_version") or ""
        )
        totals[version] += 1
    return dict(totals)


def aggregate_consumers_by_version(
    records: list[dict[str, Any]],
    package_name: str,
) -> dict[str, int]:
    consumers: dict[str, set[str]] = defaultdict(set)
    for record in records:
        dep = dep_data_from_record(record)
        name = str(dep.get("package_name") or "")
        if name != package_name:
            continue
        project_uuid = str(record.get("project_uuid") or "")
        version = str(
            dep.get("resolved_version") or dep.get("unresolved_version") or ""
        )
        if not project_uuid or not version:
            continue
        consumers[version].add(project_uuid)
    return {version: len(projects) for version, projects in consumers.items()}


def rollup_version_cardinality(
    records: list[dict[str, Any]], estate_root: str
) -> list[dict[str, Any]]:
    """Roll up distinct versions per package name from DependencyMetadata records."""
    versions_by_name: dict[str, set[str]] = defaultdict(set)
    usage_by_name: dict[str, int] = defaultdict(int)

    for record in records:
        dep = dep_data_from_record(record)
        name = str(dep.get("package_name") or "")
        if not name:
            continue
        version = str(
            dep.get("resolved_version") or dep.get("unresolved_version") or ""
        )
        if version:
            versions_by_name[name].add(version)
        usage_by_name[name] += 1

    return [
        {
            "estate_root": estate_root,
            "package_name": package_name,
            "version_cardinality": len(versions_by_name[package_name]),
            "dependency_usage_rows": usage_by_name[package_name],
        }
        for package_name in sorted(versions_by_name)
    ]
