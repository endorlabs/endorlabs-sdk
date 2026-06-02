"""Contract and metadata artifact builders for model-sync."""
# ruff: noqa: E402, C901, PERF401, E501

from __future__ import annotations

import json
import keyword
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from endorlabs.registry import RESOURCE_REGISTRY, ResourceEntry
from endorlabs.utils.model_validation import get_tags_update_paths

from .policy import MappingEntry, model_sync_entity_for_model


def facade_attr_name(entry: ResourceEntry) -> str:
    """Client attribute / endorctl --resource kind: PascalCase model class name."""
    return entry.model_class.__name__


def create_builder_slug(entry: ResourceEntry) -> str:
    """Stable snake_case slug from resource module (e.g. endorlabs.resources.api_key -> api_key)."""
    tail = entry.model_class.__module__.split(".")[-1]
    return tail if tail else entry.model_class.__name__.lower()


def _default_facade_description(model_class_name: str) -> str:
    """Human-readable one-liner when model docstring is empty."""
    return f"{model_class_name} resource facade."

_REQUIRED_RESOURCE_KEYS = {
    "attr_name",
    "resource_name",
    "model_class",
    "model_class_import_path",
    "build_create_payload_fn_name",
    "build_create_payload_fn_import_path",
    "scope",
    "parent_kind",
    "supported_ops",
    "filter_kwarg_map",
    "canonical_entities",
    "mutable_fields",
    "immutable_fields",
    "create_mode",
    "update_requires_mask",
    "identity_filter_fields",
    "workflow_flags",
    "create_convenience_spec_fields",
    "create_convenience_spec_required",
    "create_convenience_meta_fields",
    "create_convenience_payload_top_level_fields",
    "create_convenience_read_only_spec_fields",
    "convenience_skip_reason",
}


def _extract_ref_name(maybe_ref: Any) -> str | None:
    if not isinstance(maybe_ref, str):
        return None
    marker = "#/definitions/"
    if marker not in maybe_ref:
        return None
    return maybe_ref.split(marker, maxsplit=1)[1]


def _resolve_schema(definitions: dict[str, Any], node: Any) -> dict[str, Any] | None:
    """Resolve a schema node to a definition dict (follow single $ref)."""
    if not isinstance(node, dict):
        return None
    ref_name = _extract_ref_name(node.get("$ref"))
    if ref_name is not None and ref_name in definitions:
        resolved = definitions[ref_name]
        return resolved if isinstance(resolved, dict) else None
    return node


def _writable_property_names(schema: dict[str, Any]) -> list[str]:
    """Property names on a schema object that are not readOnly (definition order)."""
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return []
    names: list[str] = []
    for key, prop in properties.items():
        if not isinstance(key, str) or not isinstance(prop, dict):
            continue
        if prop.get("readOnly") is True:
            continue
        names.append(key)
    return names


def _ordered_spec_field_names(
    schema: dict[str, Any],
    *,
    writable_names: list[str],
) -> tuple[list[str], list[str]]:
    """Return (required_fields, optional_fields) preserving OpenAPI required order."""
    writable_set = set(writable_names)
    required_raw = schema.get("required")
    required: list[str] = []
    if isinstance(required_raw, list):
        required = [
            name
            for name in required_raw
            if isinstance(name, str) and name in writable_set
        ]
    required_set = set(required)
    properties = schema.get("properties")
    optional: list[str] = []
    if isinstance(properties, dict):
        for name in properties:
            if (
                isinstance(name, str)
                and name in writable_set
                and name not in required_set
            ):
                optional.append(name)
    else:
        optional = sorted(name for name in writable_names if name not in required_set)
    return required, optional


def extract_create_convenience_fields(
    definitions: dict[str, Any],
    create_body_definitions: dict[str, Any],
) -> dict[str, Any]:
    """Derive create convenience metadata from OpenAPI create body definition(s).

    Returns keys used by facade contract, payload_schemas, and create_convenience.py.
    """
    empty: dict[str, Any] = {
        "create_convenience_spec_fields": [],
        "create_convenience_spec_required": [],
        "create_convenience_meta_fields": [],
        "create_convenience_payload_top_level_fields": [],
        "create_convenience_read_only_spec_fields": [],
        "convenience_skip_reason": None,
    }
    if not create_body_definitions:
        return {**empty, "convenience_skip_reason": "no_create_body_definition"}

    # Prefer the body that exposes a top-level spec ref (standard resource create).
    body_def: dict[str, Any] | None = None
    for candidate in create_body_definitions.values():
        if not isinstance(candidate, dict):
            continue
        props = candidate.get("properties")
        if isinstance(props, dict) and "spec" in props:
            body_def = candidate
            break
    if body_def is None:
        first = next(
            (item for item in create_body_definitions.values() if isinstance(item, dict)),
            None,
        )
        body_def = first if isinstance(first, dict) else None
    if body_def is None:
        return {**empty, "convenience_skip_reason": "no_create_body_definition"}

    body_required_raw = body_def.get("required")
    body_required = (
        {name for name in body_required_raw if isinstance(name, str)}
        if isinstance(body_required_raw, list)
        else set()
    )
    properties = body_def.get("properties")
    if not isinstance(properties, dict):
        return {**empty, "convenience_skip_reason": "create_body_missing_properties"}

    spec_node = properties.get("spec")
    spec_schema = _resolve_schema(definitions, spec_node) if spec_node is not None else None
    if spec_schema is None:
        return {**empty, "convenience_skip_reason": "create_body_missing_spec"}

    # Nested spec.request (metadata query style) — no flat spec promotion.
    spec_props = spec_schema.get("properties")
    if isinstance(spec_props, dict) and "request" in spec_props:
        request_schema = _resolve_schema(definitions, spec_props.get("request"))
        if request_schema is not None:
            return {
                **empty,
                "convenience_skip_reason": "nested_spec_request",
            }

    spec_writable = _writable_property_names(spec_schema)
    spec_read_only: list[str] = []
    if isinstance(spec_props, dict):
        for key, prop in spec_props.items():
            if (
                isinstance(key, str)
                and isinstance(prop, dict)
                and prop.get("readOnly") is True
            ):
                spec_read_only.append(key)
    spec_required, spec_optional = _ordered_spec_field_names(
        spec_schema, writable_names=spec_writable
    )
    spec_fields = spec_required + spec_optional

    payload_top_level: list[str] = []
    meta_fields: list[str] = []
    for key, prop in sorted(properties.items()):
        if not isinstance(key, str) or not isinstance(prop, dict):
            continue
        if key == "spec":
            continue
        if prop.get("readOnly") is True:
            continue
        payload_top_level.append(key)
        if key == "meta":
            meta_schema = _resolve_schema(definitions, prop)
            if meta_schema is not None and "name" in _writable_property_names(meta_schema):
                if "meta" not in body_required:
                    meta_fields.append("name")

    return {
        "create_convenience_spec_fields": spec_fields,
        "create_convenience_spec_required": spec_required,
        "create_convenience_meta_fields": meta_fields,
        "create_convenience_payload_top_level_fields": payload_top_level,
        "create_convenience_read_only_spec_fields": sorted(spec_read_only),
        "convenience_skip_reason": None,
    }


def attr_name_to_constant_prefix(attr_name: str) -> str:
    """Convert PascalCase resource attr to SCREAMING_SNAKE (VectorStoreQuery -> VECTOR_STORE_QUERY)."""
    chars: list[str] = []
    for index, char in enumerate(attr_name):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.upper())
    return "".join(chars)


def render_create_convenience_module(facade_contract: dict[str, Any]) -> str:
    """Render generated create convenience constants module."""
    resources = facade_contract.get("resources")
    if not isinstance(resources, list):
        resources = []
    lines = [
        '"""Generated create convenience field lists for build_create_payload helpers."""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for resource in sorted(
        (item for item in resources if isinstance(item, dict)),
        key=lambda item: str(item.get("attr_name", "")),
    ):
        attr_name = resource.get("attr_name")
        if not isinstance(attr_name, str):
            continue
        prefix = attr_name_to_constant_prefix(attr_name)
        spec_fields = resource.get("create_convenience_spec_fields")
        spec_required = resource.get("create_convenience_spec_required")
        meta_fields = resource.get("create_convenience_meta_fields")
        if not isinstance(spec_fields, list):
            spec_fields = []
        if not isinstance(spec_required, list):
            spec_required = []
        if not isinstance(meta_fields, list):
            meta_fields = []
        spec_names = [name for name in spec_fields if isinstance(name, str)]
        spec_required_names = [
            name for name in spec_required if isinstance(name, str)
        ]
        meta_names = [name for name in meta_fields if isinstance(name, str)]
        top_level = resource.get("create_convenience_payload_top_level_fields")
        if not isinstance(top_level, list):
            top_level = []
        top_names = [name for name in top_level if isinstance(name, str)]
        lines.append(f"{prefix}_SPEC_FIELDS = {tuple(spec_names)!r}")
        lines.append(f"{prefix}_SPEC_REQUIRED = {tuple(spec_required_names)!r}")
        lines.append(f"{prefix}_META_FIELDS = {tuple(meta_names)!r}")
        lines.append(f"{prefix}_PAYLOAD_TOP_LEVEL_FIELDS = {tuple(top_names)!r}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


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


def build_operation_path_metadata(spec: dict[str, Any]) -> dict[str, Any]:
    """Build operation metadata catalog from OpenAPI paths."""
    operations: list[dict[str, Any]] = []
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return {"operation_count": 0, "operations": []}

    for path in sorted(paths):
        method_map = paths.get(path)
        if not isinstance(method_map, dict):
            continue
        for method in sorted(method_map):
            operation = method_map.get(method)
            if not isinstance(operation, dict):
                continue
            request_refs: set[str] = set()
            response_refs: set[str] = set()

            parameters = operation.get("parameters")
            if isinstance(parameters, list):
                for parameter in parameters:
                    if not isinstance(parameter, dict):
                        continue
                    request_refs.update(_collect_schema_refs(parameter))

            responses = operation.get("responses")
            if isinstance(responses, dict):
                for response in responses.values():
                    if not isinstance(response, dict):
                        continue
                    response_refs.update(_collect_schema_refs(response))

            tags = operation.get("tags")
            normalized_tags = (
                sorted(tag for tag in tags if isinstance(tag, str))
                if isinstance(tags, list)
                else []
            )
            operations.append(
                {
                    "path": path,
                    "method": method.lower(),
                    "operation_id": (
                        operation.get("operationId")
                        if isinstance(operation.get("operationId"), str)
                        else None
                    ),
                    "tags": normalized_tags,
                    "x_internal": bool(operation.get("x-internal") is True),
                    "request_refs": sorted(request_refs),
                    "response_refs": sorted(response_refs),
                }
            )

    operations = sorted(
        operations,
        key=lambda item: (item["path"], item["method"], item["operation_id"] or ""),
    )
    return {"operation_count": len(operations), "operations": operations}


def build_payload_schemas(
    *,
    spec: dict[str, Any],
    operation_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build create/update payload schema metadata by registry resource."""
    definitions = spec.get("definitions")
    if not isinstance(definitions, dict):
        definitions = {}

    operations = operation_metadata.get("operations")
    if not isinstance(operations, list):
        operations = []

    operation_rows: list[dict[str, Any]] = [
        item
        for item in operations
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("method"), str)
    ]

    def _is_collection_path(path: str, resource_name: str) -> bool:
        return path.endswith(f"/{resource_name}") and "/v1/namespaces/" in path

    def _is_item_path(path: str, resource_name: str) -> bool:
        return path.endswith(f"/{resource_name}/{{uuid}}") and "/v1/namespaces/" in path

    resources: list[dict[str, Any]] = []
    for entry in sorted(RESOURCE_REGISTRY, key=facade_attr_name):
        create_entities: set[str] = set()
        update_entities: set[str] = set()
        for operation in operation_rows:
            op_path = operation["path"]
            op_method = operation["method"]
            if not isinstance(op_path, str) or not isinstance(op_method, str):
                continue
            refs = operation.get("request_refs")
            if not isinstance(refs, list):
                continue
            if op_method == "post" and _is_collection_path(op_path, entry.resource_name):
                create_entities.update(ref for ref in refs if isinstance(ref, str))
                continue
            if op_method in {"patch", "put"} and (
                _is_collection_path(op_path, entry.resource_name)
                or _is_item_path(op_path, entry.resource_name)
            ):
                update_entities.update(ref for ref in refs if isinstance(ref, str))

        create_definitions = {
            name: definitions[name]
            for name in sorted(create_entities)
            if name in definitions
        }
        update_definitions = {
            name: definitions[name]
            for name in sorted(update_entities)
            if name in definitions
        }
        convenience = extract_create_convenience_fields(definitions, create_definitions)
        resources.append(
            {
                "attr_name": facade_attr_name(entry),
                "resource_name": entry.resource_name,
                "create_payload_entities": sorted(create_entities),
                "update_payload_entities": sorted(update_entities),
                "create_payload_definitions": create_definitions,
                "update_payload_definitions": update_definitions,
                **convenience,
            }
        )

    return {"resource_count": len(resources), "resources": resources}


def load_resource_scope_overrides(profiles_dir: Path) -> dict[str, str]:
    """Optional explicit scope overrides keyed by registry ``attr_name``."""
    path = profiles_dir / "resource_scope_overrides.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    overrides: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str):
            overrides[key] = value
    return overrides


_TENANT_NAMESPACE_PATH_TOKENS = frozenset(
    {
        "{tenant_meta.namespace}",
        "{object.tenant_meta.namespace}",
    }
)


def infer_resource_scope(
    resource_name: str,
    operation_metadata: dict[str, Any],
) -> str:
    """Infer API namespace scope from OpenAPI path namespace segments.

    Collection/item paths under ``/v1/namespaces/{tenant_meta.namespace}/…`` are
    tenant-scoped. Paths whose namespace segment is the literal ``oss`` (or
    ``system``) use that fixed plane instead.
    """
    operations = operation_metadata.get("operations")
    if not isinstance(operations, list):
        return "tenant"

    namespace_segments: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        path = operation.get("path")
        method = operation.get("method")
        if not isinstance(path, str) or not isinstance(method, str):
            continue
        if "/v1/namespaces/" not in path:
            continue
        if f"/{resource_name}" not in path and not path.endswith(f"/{resource_name}"):
            continue
        tail = path.split("/v1/namespaces/", maxsplit=1)[1]
        namespace_segments.add(tail.split("/", maxsplit=1)[0])

    if not namespace_segments:
        return "tenant"
    if namespace_segments == {"oss"}:
        return "oss"
    if namespace_segments == {"system"}:
        return "system"
    if namespace_segments & _TENANT_NAMESPACE_PATH_TOKENS:
        return "tenant"
    return "tenant"


def build_facade_contract(
    *,
    mapping_entries: list[MappingEntry],
    payload_schemas: dict[str, Any],
    operation_metadata: dict[str, Any],
    scope_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build registry/facade contract metadata for stubs and docs."""
    mapping_entities = {entry.entity_name for entry in mapping_entries}
    payload_by_attr: dict[str, dict[str, Any]] = {}
    payload_resources = payload_schemas.get("resources")
    if isinstance(payload_resources, list):
        for resource in payload_resources:
            if not isinstance(resource, dict):
                continue
            attr_name = resource.get("attr_name")
            if isinstance(attr_name, str):
                payload_by_attr[attr_name] = resource

    resources: list[dict[str, Any]] = []
    for entry in sorted(RESOURCE_REGISTRY, key=facade_attr_name):
        accepted = sorted(model_sync_entity_for_model(entry.model_class))
        canonical_entities = sorted(entity for entity in accepted if entity in mapping_entities)
        attr = facade_attr_name(entry)
        payload = payload_by_attr.get(attr, {})
        tags_paths = get_tags_update_paths(entry.model_class)
        build_create_fn = getattr(entry, "build_create_payload_fn", None)
        model_import_path = f"{entry.model_class.__module__}:{entry.model_class.__name__}"
        build_create_import_path = (
            f"{build_create_fn.__module__}:{build_create_fn.__name__}"
            if callable(build_create_fn)
            else None
        )
        mutable_fields_getter = getattr(entry.model_class, "get_mutable_fields_cls", None)
        immutable_fields_getter = getattr(entry.model_class, "get_immutable_fields_cls", None)
        mutable_fields = (
            sorted(
                value
                for value in mutable_fields_getter()
                if isinstance(value, str) and value.strip()
            )
            if callable(mutable_fields_getter)
            else []
        )
        immutable_fields = (
            sorted(
                value
                for value in immutable_fields_getter()
                if isinstance(value, str) and value.strip()
            )
            if callable(immutable_fields_getter)
            else []
        )
        supports_create = "create" in entry.supported_ops
        supports_update = "update" in entry.supported_ops
        create_mode = (
            "both"
            if supports_create and callable(build_create_fn)
            else ("payload-only" if supports_create else "unsupported")
        )
        workflow_flags: list[str] = []
        if "list" in entry.supported_ops and "get" not in entry.supported_ops:
            workflow_flags.append("list-only")
        if entry.resource_name.endswith("requests"):
            workflow_flags.append("request-style-endpoint")
        resources.append(
            {
                "attr_name": attr,
                "resource_name": entry.resource_name,
                "model_class": entry.model_class.__name__,
                "model_class_import_path": model_import_path,
                "description": (
                    (entry.model_class.__doc__ or "").strip().splitlines()[0].strip()
                    if (entry.model_class.__doc__ or "").strip()
                    else _default_facade_description(entry.model_class.__name__)
                ),
                "build_create_payload_fn_name": (
                    f"{create_builder_slug(entry)}_build_create"
                    if getattr(entry, "build_create_payload_fn", None) is not None
                    else None
                ),
                "build_create_payload_fn_import_path": build_create_import_path,
                "scope": (scope_overrides or {}).get(
                    attr, infer_resource_scope(entry.resource_name, operation_metadata)
                ),
                "parent_kind": entry.parent_kind,
                "supported_ops": sorted(entry.supported_ops),
                "filter_kwarg_map": {
                    key: value for key, value in sorted(entry.filter_kwarg_map.items())
                },
                "canonical_entities": canonical_entities,
                "accepted_canonical_entities": accepted,
                "has_tag_methods": "meta.tags" in tags_paths and "update" in entry.supported_ops,
                "mutable_fields": mutable_fields,
                "immutable_fields": immutable_fields,
                "create_mode": create_mode,
                "update_requires_mask": supports_update,
                "identity_filter_fields": sorted(entry.filter_kwarg_map),
                "workflow_flags": sorted(workflow_flags),
                "create_payload_entities": payload.get("create_payload_entities", []),
                "update_payload_entities": payload.get("update_payload_entities", []),
                "create_convenience_spec_fields": payload.get(
                    "create_convenience_spec_fields", []
                ),
                "create_convenience_spec_required": payload.get(
                    "create_convenience_spec_required", []
                ),
                "create_convenience_meta_fields": payload.get(
                    "create_convenience_meta_fields", []
                ),
                "create_convenience_payload_top_level_fields": payload.get(
                    "create_convenience_payload_top_level_fields", []
                ),
                "create_convenience_read_only_spec_fields": payload.get(
                    "create_convenience_read_only_spec_fields", []
                ),
                "convenience_skip_reason": payload.get("convenience_skip_reason"),
            }
        )
    return {"resource_count": len(resources), "resources": resources}


def build_runtime_index_metadata(facade_contract: dict[str, Any]) -> dict[str, Any]:
    """Build importable runtime index metadata from facade contract rows."""
    resources = facade_contract.get("resources")
    if not isinstance(resources, list):
        resources = []
    model_class_import_by_name: dict[str, str] = {}
    create_builder_import_by_name: dict[str, str] = {}
    mutability_by_resource: dict[str, dict[str, list[str]]] = {}
    capability_by_resource: dict[str, dict[str, Any]] = {}
    for item in resources:
        if not isinstance(item, dict):
            continue
        model_class_name = item.get("model_class")
        model_class_import_path = item.get("model_class_import_path")
        if isinstance(model_class_name, str) and isinstance(model_class_import_path, str):
            model_class_import_by_name[model_class_name] = model_class_import_path
        build_create_payload_fn_name = item.get("build_create_payload_fn_name")
        build_create_payload_fn_import_path = item.get("build_create_payload_fn_import_path")
        if (
            isinstance(build_create_payload_fn_name, str)
            and isinstance(build_create_payload_fn_import_path, str)
        ):
            create_builder_import_by_name[build_create_payload_fn_name] = (
                build_create_payload_fn_import_path
            )
        resource_name = item.get("resource_name")
        mutable_fields = item.get("mutable_fields")
        immutable_fields = item.get("immutable_fields")
        if (
            isinstance(resource_name, str)
            and isinstance(mutable_fields, list)
            and isinstance(immutable_fields, list)
        ):
            mutability_by_resource[resource_name] = {
                "mutable_fields": sorted(
                    value for value in mutable_fields if isinstance(value, str)
                ),
                "immutable_fields": sorted(
                    value for value in immutable_fields if isinstance(value, str)
                ),
            }
        if isinstance(resource_name, str):
            capability_by_resource[resource_name] = {
                "create_mode": item.get("create_mode", "unsupported"),
                "update_requires_mask": bool(item.get("update_requires_mask")),
                "identity_filter_fields": sorted(
                    value
                    for value in item.get("identity_filter_fields", [])
                    if isinstance(value, str)
                ),
                "workflow_flags": sorted(
                    value for value in item.get("workflow_flags", []) if isinstance(value, str)
                ),
            }
    return {
        "model_class_import_by_name": {
            key: value for key, value in sorted(model_class_import_by_name.items())
        },
        "create_builder_import_by_name": {
            key: value for key, value in sorted(create_builder_import_by_name.items())
        },
        "mutability_by_resource": {
            key: value for key, value in sorted(mutability_by_resource.items())
        },
        "capability_by_resource": {
            key: value for key, value in sorted(capability_by_resource.items())
        },
    }


def render_generated_registry_contract_module(
    *,
    facade_contract: dict[str, Any],
    provenance: dict[str, Any],
) -> str:
    """Render deterministic Python module content for runtime registry contract."""
    resources = facade_contract.get("resources")
    if not isinstance(resources, list):
        resources = []
    normalized_resources = sorted(
        (
            resource
            for resource in resources
            if isinstance(resource, dict) and isinstance(resource.get("attr_name"), str)
        ),
        key=lambda item: item["attr_name"],
    )
    payload = {
        "resource_count": len(normalized_resources),
        "resources": normalized_resources,
    }
    endorctl_version = provenance.get("endorctl_version", "unknown")
    spec_sha256 = provenance.get("spec_sha256", "unknown")
    compact_provenance = json.dumps(
        {
            "endorctl_version": endorctl_version,
            "spec_sha256": spec_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        '"""Generated runtime registry contract for facade construction."""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n\n"
        f"# generated by model-sync\n"
        f"# endorctl_version: {endorctl_version}\n"
        f"# spec_sha256: {spec_sha256}\n\n"
        f"# model_sync_provenance: {compact_provenance}\n\n"
        "RUNTIME_REGISTRY_CONTRACT = json.loads(\n"
        "    r'''"
        + json.dumps(payload, indent=2, sort_keys=True)
        + "'''\n"
        ")\n"
    )


def build_registry_parity_report(
    *,
    mapping_entries: list[MappingEntry],
    facade_contract: dict[str, Any],
) -> dict[str, Any]:
    """Build parity report between mapping output and resource registry models."""
    mapping_entity_names = {entry.entity_name for entry in mapping_entries}
    resources = facade_contract.get("resources")
    if not isinstance(resources, list):
        resources = []

    missing_in_mapping: list[str] = []
    alias_matches: list[dict[str, str]] = []
    accepted_entities: set[str] = set()
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        attr_name = resource.get("attr_name")
        accepted = resource.get("accepted_canonical_entities")
        canonical = resource.get("canonical_entities")
        if not isinstance(attr_name, str):
            continue
        accepted_set = {value for value in accepted or [] if isinstance(value, str)}
        canonical_set = {value for value in canonical or [] if isinstance(value, str)}
        accepted_entities.update(accepted_set)
        if not canonical_set:
            missing_in_mapping.append(attr_name)
        alias_only = sorted(canonical_set - {f"v1{resource.get('model_class', '')}"})
        for entity_name in alias_only:
            alias_matches.append({"attr_name": attr_name, "entity_name": entity_name})

    mapping_without_registry_match = sorted(mapping_entity_names - accepted_entities)
    # Extra spec entities without registry exposure are expected for
    # intentionally unsupported/internal API surfaces; parity fails only when a
    # registry resource has no canonical mapping.
    status = "pass" if not missing_in_mapping else "fail"
    return {
        "status": status,
        "missing_in_mapping": sorted(missing_in_mapping),
        "mapping_without_registry_match": mapping_without_registry_match,
        "alias_matches": sorted(
            alias_matches, key=lambda item: (item["attr_name"], item["entity_name"])
        ),
    }


def validate_contract_artifacts(
    *,
    facade_contract: dict[str, Any],
    registry_parity_report: dict[str, Any],
    operation_path_metadata: dict[str, Any],
    payload_schemas: dict[str, Any],
) -> list[str]:
    """Validate artifact schemas and invariants; return errors."""
    errors: list[str] = []

    resources = facade_contract.get("resources")
    if not isinstance(resources, list) or not resources:
        errors.append("facade_contract.resources must be a non-empty list")
    else:
        seen_attr_names: list[str] = []
        for index, resource in enumerate(resources):
            if not isinstance(resource, dict):
                errors.append(f"facade_contract.resources[{index}] must be an object")
                continue
            missing_keys = sorted(_REQUIRED_RESOURCE_KEYS - set(resource))
            if missing_keys:
                errors.append(
                    f"facade_contract.resources[{index}] missing keys: {', '.join(missing_keys)}"
                )
            canonical_entities = resource.get("canonical_entities")
            if not isinstance(canonical_entities, list):
                errors.append(
                    f"facade_contract.resources[{index}].canonical_entities must be a list"
                )
            if not isinstance(resource.get("model_class_import_path"), str):
                errors.append(
                    f"facade_contract.resources[{index}].model_class_import_path must be a string"
                )
            for key in ("mutable_fields", "immutable_fields"):
                value = resource.get(key)
                if not isinstance(value, list):
                    errors.append(f"facade_contract.resources[{index}].{key} must be a list")
            if resource.get("create_mode") not in {"both", "payload-only", "unsupported"}:
                errors.append(
                    f"facade_contract.resources[{index}].create_mode has invalid value"
                )
            if not isinstance(resource.get("update_requires_mask"), bool):
                errors.append(
                    f"facade_contract.resources[{index}].update_requires_mask must be bool"
                )
            if not isinstance(resource.get("identity_filter_fields"), list):
                errors.append(
                    f"facade_contract.resources[{index}].identity_filter_fields must be list"
                )
            if not isinstance(resource.get("workflow_flags"), list):
                errors.append(
                    f"facade_contract.resources[{index}].workflow_flags must be list"
                )
            for key in (
                "create_convenience_spec_fields",
                "create_convenience_spec_required",
                "create_convenience_meta_fields",
                "create_convenience_payload_top_level_fields",
                "create_convenience_read_only_spec_fields",
            ):
                value = resource.get(key)
                if not isinstance(value, list):
                    errors.append(
                        f"facade_contract.resources[{index}].{key} must be a list"
                    )
            skip_reason = resource.get("convenience_skip_reason")
            if skip_reason is not None and not isinstance(skip_reason, str):
                errors.append(
                    f"facade_contract.resources[{index}].convenience_skip_reason "
                    "must be string or null"
                )
            create_mode = resource.get("create_mode")
            spec_fields = resource.get("create_convenience_spec_fields")
            if (
                create_mode == "both"
                and isinstance(spec_fields, list)
                and not spec_fields
                and skip_reason is None
            ):
                errors.append(
                    f"facade_contract.resources[{index}]: create_mode=both requires "
                    "create_convenience_spec_fields or convenience_skip_reason"
                )

            attr_name = resource.get("attr_name")
            model_class = resource.get("model_class")
            if isinstance(attr_name, str) and isinstance(model_class, str):
                seen_attr_names.append(attr_name)
                if attr_name != model_class:
                    errors.append(
                        f"facade_contract.resources[{index}]: attr_name must equal "
                        f"model_class for endorctl parity (got {attr_name!r} vs "
                        f"{model_class!r})"
                    )
                if not attr_name.isidentifier():
                    errors.append(
                        f"facade_contract.resources[{index}]: attr_name must be a "
                        f"valid Python identifier (got {attr_name!r})"
                    )
                if keyword.iskeyword(attr_name):
                    errors.append(
                        f"facade_contract.resources[{index}]: attr_name must not be "
                        f"a Python keyword (got {attr_name!r})"
                    )

        if len(seen_attr_names) != len(set(seen_attr_names)):
            errors.append(
                "facade_contract.resources: attr_name values must be unique "
                f"(endorctl resource kinds); duplicates: "
                f"{sorted({a for a in seen_attr_names if seen_attr_names.count(a) > 1})}"
            )

    if registry_parity_report.get("status") not in {"pass", "fail"}:
        errors.append("registry_parity_report.status must be 'pass' or 'fail'")
    for key in ("missing_in_mapping", "mapping_without_registry_match", "alias_matches"):
        if not isinstance(registry_parity_report.get(key), list):
            errors.append(f"registry_parity_report.{key} must be a list")

    operations = operation_path_metadata.get("operations")
    if not isinstance(operations, list) or not operations:
        errors.append("operation_path_metadata.operations must be a non-empty list")
    else:
        required_operation_keys = {
            "path",
            "method",
            "operation_id",
            "tags",
            "x_internal",
            "request_refs",
            "response_refs",
        }
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                errors.append(
                    f"operation_path_metadata.operations[{index}] must be an object"
                )
                continue
            missing_keys = sorted(required_operation_keys - set(operation))
            if missing_keys:
                errors.append(
                    "operation_path_metadata.operations"
                    f"[{index}] missing keys: {', '.join(missing_keys)}"
                )

    payload_resources = payload_schemas.get("resources")
    if not isinstance(payload_resources, list) or not payload_resources:
        errors.append("payload_schemas.resources must be a non-empty list")
    else:
        required_payload_keys = {
            "attr_name",
            "resource_name",
            "create_payload_entities",
            "update_payload_entities",
            "create_payload_definitions",
            "update_payload_definitions",
            "create_convenience_spec_fields",
            "create_convenience_spec_required",
            "create_convenience_meta_fields",
            "create_convenience_payload_top_level_fields",
            "create_convenience_read_only_spec_fields",
            "convenience_skip_reason",
        }
        for index, resource in enumerate(payload_resources):
            if not isinstance(resource, dict):
                errors.append(f"payload_schemas.resources[{index}] must be an object")
                continue
            missing_keys = sorted(required_payload_keys - set(resource))
            if missing_keys:
                errors.append(
                    f"payload_schemas.resources[{index}] missing keys: {', '.join(missing_keys)}"
                )

    return errors
