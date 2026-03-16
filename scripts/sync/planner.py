"""Planning phase for deterministic model-sync generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .policy import MappingEntry, build_mapping_entries


@dataclass(frozen=True)
class PlanResult:
    """Deterministic plan output."""

    entries: list[MappingEntry]
    grouped_entities: dict[str, list[str]]
    schema_shards: dict[str, dict[str, Any]]


def _collect_ref_dependencies(node: Any) -> set[str]:
    """Recursively collect local definition refs from a JSON schema node."""
    refs: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/definitions/"):
            refs.add(ref.split("#/definitions/", maxsplit=1)[1])
        for value in node.values():
            refs.update(_collect_ref_dependencies(value))
    elif isinstance(node, list):
        for value in node:
            refs.update(_collect_ref_dependencies(value))
    return refs


def _expand_definition_closure(
    definitions: dict[str, Any],
    root_entities: list[str],
) -> list[str]:
    """Expand entity list to include transitive definition dependencies."""
    ordered: list[str] = []
    seen: set[str] = set()
    queue = list(root_entities)
    while queue:
        name = queue.pop(0)
        if name in seen or name not in definitions:
            continue
        seen.add(name)
        ordered.append(name)
        queue.extend(sorted(_collect_ref_dependencies(definitions[name]) - seen))
    return sorted(ordered)


def build_plan(spec: dict[str, Any]) -> PlanResult:
    """Build deterministic codegen plan from OpenAPI spec."""
    entries = build_mapping_entries(spec)
    definitions = spec.get("definitions")
    if not isinstance(definitions, dict):
        raise TypeError("Spec has no definitions map")

    grouped: dict[str, list[str]] = {}
    for entry in entries:
        if entry.entity_name in definitions:
            grouped.setdefault(entry.module_path, []).append(entry.entity_name)

    grouped = {module: sorted(set(names)) for module, names in sorted(grouped.items())}
    shards: dict[str, dict[str, Any]] = {}
    for module_path, entity_names in grouped.items():
        expanded_entities = _expand_definition_closure(definitions, entity_names)
        shards[module_path] = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": module_path.replace("/", "_"),
            "type": "object",
            "properties": {
                name: {"$ref": f"#/definitions/{name}"} for name in entity_names
            },
            "definitions": {name: definitions[name] for name in expanded_entities},
        }
    return PlanResult(entries=entries, grouped_entities=grouped, schema_shards=shards)


def write_mapping_metadata(
    entries: list[MappingEntry],
    output_path: Path,
    profiles: dict[str, Any],
) -> None:
    """Write canonical entity mapping metadata with profiles."""
    payload: dict[str, Any] = {
        "entry_count": len(entries),
        "entries": [
            {
                "entity_name": entry.entity_name,
                "module_path": entry.module_path,
                "source_kind": entry.source_kind,
                "source_key": entry.source_key,
                "operation_id": entry.operation_id,
            }
            for entry in entries
        ],
        "profiles": profiles,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
