"""Deterministic policy for model-sync mapping."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")
_COMMON_SUFFIXES = (
    "Spec",
    "Meta",
    "Body",
    "Request",
    "Response",
    "Result",
    "Status",
    "Config",
    "Record",
    "Data",
)

MODEL_SYNC_ENTITY_ALIASES_BY_MODEL: dict[str, str] = {
    "Metric": "MetricServiceCreateMetricBody",
    "Vulnerability": "v1Vuln",
}


def _canonical_entity_for_model_name(model_name: str) -> str:
    """Return canonical OpenAPI entity name for a model class name.

    Most models map to ``v1<ModelName>``; generated classes already prefixed
    with ``V1`` map to ``v1<suffix>`` (e.g. ``V1Query`` -> ``v1Query``).
    """
    if model_name.startswith("V1") and len(model_name) > 2:
        return f"v1{model_name[2:]}"
    return f"v1{model_name}"


@dataclass(frozen=True)
class SpecEntity:
    """One model-worthy OpenAPI entity."""

    entity_name: str
    source_kind: str
    source_key: str
    operation_id: str | None = None
    service_hint: str | None = None
    is_internal: bool = False


@dataclass(frozen=True)
class MappingEntry:
    """One deterministic map entry from entity to module."""

    entity_name: str
    module_path: str
    source_kind: str
    source_key: str
    operation_id: str | None


def load_openapi_spec(path: Path) -> dict[str, Any]:
    """Load OpenAPI/Swagger JSON document."""
    return json.loads(path.read_text(encoding="utf-8"))


def camel_to_snake(name: str) -> str:
    """Convert CamelCase-ish names to snake_case."""
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    if not normalized:
        return "unknown"
    with_boundaries = _CAMEL_BOUNDARY.sub("_", normalized)
    return re.sub(r"_+", "_", with_boundaries).lower()


def modeled_resource_exception_entities() -> set[str]:
    """Return canonical exception entities for eligibility checks."""
    try:
        from endorlabs.registry import RESOURCE_REGISTRY
    except Exception:
        return set()
    entities = {
        _canonical_entity_for_model_name(entry.model_class.__name__)
        for entry in RESOURCE_REGISTRY
        if getattr(entry, "model_class", None) is not None
    }
    entities.update(MODEL_SYNC_ENTITY_ALIASES_BY_MODEL.values())
    return entities


def model_sync_entity_for_model(model_class: type[Any]) -> set[str]:
    """Return accepted canonical entity names for a model class."""
    model_name = model_class.__name__
    accepted = {_canonical_entity_for_model_name(model_name)}
    alias = MODEL_SYNC_ENTITY_ALIASES_BY_MODEL.get(model_name)
    if alias:
        accepted.add(alias)
    return accepted


def _extract_ref_name(maybe_ref: Any) -> str | None:
    if not isinstance(maybe_ref, str):
        return None
    marker = "#/definitions/"
    if marker not in maybe_ref:
        return None
    return maybe_ref.split(marker, maxsplit=1)[1]


def _collect_schema_refs(node: Any) -> set[str]:
    """Recursively collect #/definitions refs from nested schema nodes."""
    refs: set[str] = set()
    if isinstance(node, dict):
        ref_name = _extract_ref_name(node.get("$ref"))
        if ref_name is not None:
            refs.add(ref_name)
        for value in node.values():
            refs.update(_collect_schema_refs(value))
    elif isinstance(node, list):
        for value in node:
            refs.update(_collect_schema_refs(value))
    return refs


def _service_from_entity_name(entity_name: str) -> str | None:
    if "Service" in entity_name:
        return entity_name.split("Service", maxsplit=1)[0] or None
    base = entity_name[2:] if entity_name.startswith("v1") and len(entity_name) > 2 else entity_name
    for suffix in _COMMON_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            base = base[: -len(suffix)]
            break
    tokens = [token for token in _CAMEL_BOUNDARY.sub("_", base).split("_") if token]
    if not tokens:
        return None
    head = tokens[0]
    if len(tokens) >= 2 and head.lower() in {
        "query",
        "scan",
        "repository",
        "package",
        "policy",
        "authorization",
        "authentication",
        "agent",
        "artifact",
        "dashboard",
        "ai",
        "version",
        "code",
        "notification",
    }:
        return f"{tokens[0]}{tokens[1]}"
    return head


def extract_spec_entities(spec: dict[str, Any]) -> list[SpecEntity]:  # noqa: C901
    """Extract model-worthy entities from definitions and operation refs."""
    entities: dict[tuple[str, str], SpecEntity] = {}
    definitions = spec.get("definitions")
    if isinstance(definitions, dict):
        for name in sorted(definitions):
            entities[("definition", name)] = SpecEntity(
                entity_name=name,
                source_kind="definition",
                source_key=name,
                service_hint=_service_from_entity_name(name),
                is_internal=False,
            )

    paths = spec.get("paths")
    if isinstance(paths, dict):
        for path in sorted(paths):
            operation_map = paths.get(path)
            if not isinstance(operation_map, dict):
                continue
            for method in sorted(operation_map):
                operation = operation_map.get(method)
                if not isinstance(operation, dict):
                    continue
                operation_id = operation.get("operationId")
                tags = operation.get("tags")
                is_internal = bool(operation.get("x-internal") is True)
                service_hint = tags[0] if isinstance(tags, list) and tags and isinstance(tags[0], str) else None
                if service_hint is None and isinstance(operation_id, str):
                    service_hint = operation_id

                parameters = operation.get("parameters")
                if isinstance(parameters, list):
                    for parameter in parameters:
                        if not isinstance(parameter, dict):
                            continue
                        refs = _collect_schema_refs(parameter)
                        for ref_name in sorted(refs):
                            key = ("operation_ref", f"{path}:{method}:{ref_name}")
                            entities[key] = SpecEntity(
                                entity_name=ref_name,
                                source_kind="operation_ref",
                                source_key=f"{path}:{method}",
                                operation_id=operation_id if isinstance(operation_id, str) else None,
                                service_hint=service_hint,
                                is_internal=is_internal,
                            )

                responses = operation.get("responses")
                if isinstance(responses, dict):
                    for status in sorted(responses):
                        response = responses.get(status)
                        if not isinstance(response, dict):
                            continue
                        schema = response.get("schema")
                        if not isinstance(schema, dict):
                            continue
                        for ref_name in sorted(_collect_schema_refs(schema)):
                            key = ("operation_ref", f"{path}:{method}:{status}:{ref_name}")
                            entities[key] = SpecEntity(
                                entity_name=ref_name,
                                source_kind="operation_ref",
                                source_key=f"{path}:{method}:{status}",
                                operation_id=operation_id if isinstance(operation_id, str) else None,
                                service_hint=service_hint,
                                is_internal=is_internal,
                            )

    return sorted(
        entities.values(),
        key=lambda entity: (entity.entity_name, entity.source_kind, entity.source_key),
    )


def filter_eligible_entities(entities: list[SpecEntity]) -> list[SpecEntity]:
    """Apply x-internal + exception allowlist eligibility policy."""
    exceptions = modeled_resource_exception_entities()
    public_operation_entities = {
        entity.entity_name
        for entity in entities
        if entity.source_kind == "operation_ref" and not entity.is_internal
    }
    eligible: list[SpecEntity] = []
    for entity in entities:
        if entity.source_kind == "operation_ref":
            if not entity.is_internal:
                eligible.append(entity)
            continue
        if entity.entity_name in public_operation_entities or entity.entity_name in exceptions:
            eligible.append(entity)
    return eligible


def determine_partition_module(entity: SpecEntity) -> str:
    """Map entity to deterministic module path."""
    service_source = entity.service_hint or _service_from_entity_name(entity.entity_name)
    service = camel_to_snake(service_source) if service_source else "misc"
    if service == "misc":
        first = camel_to_snake(entity.entity_name)[:1] or "x"
        return f"misc/{first}"
    return service


def build_mapping_entries(spec: dict[str, Any]) -> list[MappingEntry]:
    """Build deterministic map entries from eligible entities."""
    entities = filter_eligible_entities(extract_spec_entities(spec))
    by_entity_name: dict[str, list[SpecEntity]] = {}
    for entity in entities:
        by_entity_name.setdefault(entity.entity_name, []).append(entity)

    entries: list[MappingEntry] = []
    for entity_name, candidates in sorted(by_entity_name.items()):
        preferred = sorted(
            candidates,
            key=lambda candidate: (
                0 if candidate.source_kind == "operation_ref" else 1,
                0 if candidate.service_hint else 1,
                candidate.source_key,
            ),
        )[0]
        entries.append(
            MappingEntry(
                entity_name=entity_name,
                module_path=determine_partition_module(preferred),
                source_kind=preferred.source_kind,
                source_key=preferred.source_key,
                operation_id=preferred.operation_id,
            )
        )
    return sorted(
        entries,
        key=lambda entry: (
            entry.module_path,
            entry.entity_name,
            entry.source_kind,
            entry.source_key,
        ),
    )
