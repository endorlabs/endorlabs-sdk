"""Generate Client stub (.pyi) from RESOURCE_REGISTRY and CUSTOM_FACADE_REGISTRY.

Single source of truth: the registry. Run from repo root with:
  uv run python devtools/generate_client_stub.py
Writes src/endorlabs/client_surface.pyi so Pyright types client.Project, etc.

Each resource gets a dedicated stub class (e.g. ``_ProjectFacade``) that
inherits ``ResourceRuntimeFacade[Project]``, ``ListableFacade[Model]``, or a
specialized runtime facade from ``FACADE_CLASS_BY_ATTR`` (e.g. ``ProjectFacade``).
``list()`` and ``Client.__init__`` are emitted explicitly for IDE hovers.
"""
# ruff: noqa: E402, I001, C901, E501, PERF401, PERF402

from __future__ import annotations

import inspect
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add src so we can import endorlabs.registry
from sync.path_safety import find_repo_root

repo_root = find_repo_root(start=Path(__file__).resolve().parent)
src = repo_root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
devtools_dir = repo_root / "devtools"
if str(devtools_dir) not in sys.path:
    sys.path.insert(0, str(devtools_dir))

from endorlabs.client_surface import Client as RuntimeClient
from endorlabs.facade import ListableFacade, ResourceRuntimeFacade
from endorlabs.facade.route_host import RouteHostMixin
from endorlabs.facade.specialized import FACADE_CLASS_BY_ATTR
from endorlabs.registry_overlay import merge_generated_contract_with_overlay
from endorlabs.registry import (
    CUSTOM_FACADE_REGISTRY,
    EXPERIMENTAL_REGISTRY_ATTR_NAMES,
    RESOURCE_REGISTRY,
    ResourceEntry,
)
from sync.policy import model_sync_entity_for_model

logger = logging.getLogger(__name__)


def _load_model_sync_entities() -> set[str]:
    """Load canonical entity names from the committed runtime registry contract."""
    try:
        from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    except ImportError:
        return set()
    resources = RUNTIME_REGISTRY_CONTRACT.get("resources")
    if not isinstance(resources, list):
        return set()
    entity_names: set[str] = set()
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        canonical = resource.get("canonical_entities")
        if isinstance(canonical, list):
            entity_names.update(value for value in canonical if isinstance(value, str))
    return entity_names
RESOURCE_DESCRIPTION_OVERLAY_PATH = (
    repo_root / "devtools" / "model_sync_profiles" / "resource_descriptions.json"
)

# ---------------------------------------------------------------------------
# Resource descriptions — validated from OpenAPI spec + local user docs
# ---------------------------------------------------------------------------
RESOURCE_DESCRIPTIONS: dict[str, str] = {}


def _load_description_overlay() -> dict[str, str]:
    if not RESOURCE_DESCRIPTION_OVERLAY_PATH.exists():
        return {}
    payload = json.loads(RESOURCE_DESCRIPTION_OVERLAY_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    overlay: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, str) and value.strip():
            overlay[key] = value.strip()
    return overlay


def _default_description_from_attr(attr_name: str) -> str:
    """Fallback stub description (overlay keys match endorctl kind / model class name)."""
    if "_" in attr_name:
        return f"{attr_name.replace('_', ' ').title()} resource facade."
    return f"{attr_name} resource facade."


# ---------------------------------------------------------------------------
# Per-resource class builder
# ---------------------------------------------------------------------------


def _specialized_facade_name(entry: ResourceEntry) -> str | None:
    """Runtime specialized facade class name when ``FACADE_CLASS_BY_ATTR`` applies."""
    facade_cls = FACADE_CLASS_BY_ATTR.get(entry.attr_name)
    return facade_cls.__name__ if facade_cls is not None else None


def _stub_base_class(entry: ResourceEntry) -> str:
    """PEP 695 or specialized base for per-resource stub classes."""
    specialized = _specialized_facade_name(entry)
    if specialized:
        return specialized
    model_name = entry.model_class.__name__
    if any(op in entry.supported_ops for op in ("create", "update", "delete")):
        return f"ResourceRuntimeFacade[{model_name}]"
    return f"ListableFacade[{model_name}]"


def _stub_impl_classes(entry: ResourceEntry) -> list[type[Any]]:
    """Classes consulted for inherited route/sugar method resolution."""
    classes: list[type[Any]] = []
    facade_cls = FACADE_CLASS_BY_ATTR.get(entry.attr_name)
    if facade_cls is not None:
        classes.append(facade_cls)
    classes.extend([RouteHostMixin, ResourceRuntimeFacade, ListableFacade])
    return classes


def _method_impl_class(name: str, classes: list[type[Any]]) -> type[Any] | None:
    """Return the first class in *classes* that defines *name* in its own dict."""
    for cls in classes:
        if name in cls.__dict__:
            return cls
    return None


def _stub_extra_methods(entry: ResourceEntry) -> list[str]:
    """Declare get on ListableFacade bases so create/update/delete stay hidden."""
    if (
        _stub_base_class(entry).startswith("ListableFacade")
        and "get" in entry.supported_ops
    ):
        return ["get"]
    return []


def _load_route_public_methods(attr_name: str) -> list[str]:
    try:
        from endorlabs.generated.route_contract import ROUTE_CONTRACT
    except ImportError:
        return []
    seen: set[str] = set()
    methods: list[str] = []
    for edge in ROUTE_CONTRACT.edges_for_attr(attr_name):
        public = edge.public_method
        if not public or "." not in public:
            continue
        _, method_name = public.split(".", 1)
        if method_name in seen:
            continue
        seen.add(method_name)
        methods.append(method_name)
    return methods


def _first_docstring_paragraph(obj: Any) -> str | None:
    """First paragraph of a docstring for stub hovers."""
    doc = inspect.getdoc(obj)
    if not doc:
        return None
    paragraph = doc.strip().split("\n\n", maxsplit=1)[0].strip()
    return paragraph.replace('"""', "'") if paragraph else None


def _emit_route_method_stubs(entry: ResourceEntry) -> list[str]:
    """Emit typed route accessors when not already defined on the stub base chain."""
    methods = _load_route_public_methods(entry.attr_name)
    if not methods:
        return []
    impl_classes = _stub_impl_classes(entry)
    model_name = entry.model_class.__name__
    lines: list[str] = []
    for name in methods:
        impl_cls = _method_impl_class(name, impl_classes)
        if impl_cls is not None:
            continue
        lines.append("")
        lines.extend(
            _format_method_override(
                name,
                model_name,
                source_class=ResourceRuntimeFacade,
            )
        )
    return lines


def _specialized_facade_public_methods(facade_cls: type[Any]) -> list[str]:
    """Public callables defined on a specialized facade class body."""
    names: list[str] = []
    for name, obj in facade_cls.__dict__.items():
        if name.startswith("_"):
            continue
        if callable(obj):
            names.append(name)
    return sorted(names)


def _emit_specialized_facade_stubs(entry: ResourceEntry) -> list[str]:
    """Re-emit specialized facade methods on ``_XFacade`` for agent Read discovery."""
    facade_cls = FACADE_CLASS_BY_ATTR.get(entry.attr_name)
    if facade_cls is None:
        return []
    model_name = entry.model_class.__name__
    lines: list[str] = []
    for name in _specialized_facade_public_methods(facade_cls):
        lines.append("")
        lines.extend(
            _format_method_override(
                name,
                model_name,
                source_class=facade_cls,
                include_doc=True,
            )
        )
    return lines


def _format_annotation(ann: Any, model_name: str) -> str:
    if ann is inspect.Parameter.empty:
        return ""
    s = str(ann) if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
    return re.sub(r"\bT\b", model_name, s)


_CREATE_STUB_RESERVED_PARAMS = frozenset(
    {"payload", "namespace", "name", "description", "namespace_uuid", "self"}
)

_STUB_FIELD_TYPES: dict[str, str] = {
    "metadata_filter": "dict[str, Any]",
    "raw": "dict[str, Any]",
    "project_selector": "dict[str, Any]",
    "project_exceptions": "dict[str, Any]",
    "template_values": "dict[str, Any]",
    "template_parameters": "dict[str, Any]",
    "query_statements": "dict[str, Any]",
    "permissions": "dict[str, Any]",
    "claims": "dict[str, Any]",
    "patterns": "dict[str, Any]",
    "data": "dict[str, Any]",
    "metric_values": "dict[str, Any]",
}


def _create_param_annotation(field_name: str, *, required: bool) -> str:
    base = _STUB_FIELD_TYPES.get(field_name, "Any")
    if required:
        return base.removesuffix(" | None") if base.endswith(" | None") else base
    if base == "Any":
        return "Any | None"
    if "| None" in base:
        return base
    return f"{base} | None"


def _emit_create_override(
    entry: ResourceEntry,
    contract_row: dict[str, Any],
) -> list[str]:
    """Emit typed ``create()`` when OpenAPI convenience metadata is present."""
    if "create" not in entry.supported_ops:
        return []
    create_mode = contract_row.get("create_mode")
    if create_mode != "both":
        return []
    skip_reason = contract_row.get("convenience_skip_reason")
    spec_fields_raw = contract_row.get("create_convenience_spec_fields")
    meta_fields_raw = contract_row.get("create_convenience_meta_fields")
    spec_fields = (
        [name for name in spec_fields_raw if isinstance(name, str)]
        if isinstance(spec_fields_raw, list)
        else []
    )
    meta_fields = (
        [name for name in meta_fields_raw if isinstance(name, str)]
        if isinstance(meta_fields_raw, list)
        else []
    )
    if skip_reason and not spec_fields and not meta_fields:
        return []
    if not spec_fields and not meta_fields:
        return []

    model_name = entry.model_class.__name__
    payload_name = f"Create{model_name}Payload"
    required_spec = {
        name
        for name in contract_row.get("create_convenience_spec_required", [])
        if isinstance(name, str)
    }

    params: list[str] = [
        "    def create(",
        "        self,",
        f"        payload: {payload_name} | None = None,",
        "        *,",
        "        name: str | None = None,",
        "        description: str | None = None,",
        "        namespace_uuid: str | None = None,",
        "        namespace: str | None = None,",
    ]
    for field in meta_fields:
        if field in _CREATE_STUB_RESERVED_PARAMS:
            continue
        ann = _create_param_annotation(field, required=False)
        params.append(f"        {field}: {ann} = None,")
    for field in spec_fields:
        if field in _CREATE_STUB_RESERVED_PARAMS:
            continue
        ann = _create_param_annotation(field, required=field in required_spec)
        if field in required_spec:
            params.append(f"        {field}: {ann},")
        else:
            params.append(f"        {field}: {ann} = None,")
    params.append("        **kwargs: Any,")
    params.append(f"    ) -> {model_name}:")
    params.append("        ...")
    return params


def _format_method_override(
    name: str,
    model_name: str,
    *,
    source_class: type[Any] | None = None,
    include_doc: bool = False,
) -> list[str]:
    cls = source_class or ResourceRuntimeFacade
    method = getattr(cls, name)
    sig = inspect.signature(method)
    params: list[str] = []
    saw_keyword_only = False
    for pname, param in sig.parameters.items():
        if pname == "self":
            params.append("        self,")
            continue
        if param.kind == inspect.Parameter.KEYWORD_ONLY and not saw_keyword_only:
            params.append("        *,")
            saw_keyword_only = True
        ann = _format_annotation(param.annotation, model_name)
        ann_str = f": {ann}" if ann else ""
        default = " = ..." if param.default is not inspect.Parameter.empty else ""
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            params.append(f"        **{pname}{ann_str},")
        else:
            params.append(f"        {pname}{ann_str}{default},")
    ret = _format_annotation(sig.return_annotation, model_name)
    lines: list[str] = [
        f"    def {name}(",
        *params,
        f"    ) -> {ret}:",
    ]
    if include_doc:
        doc_para = _first_docstring_paragraph(method)
        if doc_para:
            lines.append(f'        """{doc_para}"""')
    lines.append("        ...")
    return lines


def _emit_list_override(model_name: str) -> list[str]:
    """Explicit ``list()`` on stub facades for reliable IDE hovers."""
    return _format_method_override(
        "list",
        model_name,
        source_class=ListableFacade,
        include_doc=True,
    )


def _format_init_param(param: inspect.Parameter) -> str:
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        ann_str = ""
    elif isinstance(ann, str):
        ann_str = f": {ann}"
    else:
        ann_str = f": {getattr(ann, '__name__', str(ann))}"
    default = " = ..." if param.default is not inspect.Parameter.empty else ""
    if param.kind == inspect.Parameter.VAR_KEYWORD:
        return f"        **{param.name}{ann_str},"
    return f"        {param.name}{ann_str}{default},"


def _wrap_doc_text(text: str, *, first_line_width: int, body_width: int) -> list[str]:
    """Wrap docstring text for stub emission under line-length limits."""
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    limit = first_line_width
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= limit:
            current = candidate
            continue
        lines.append(current)
        current = word
        limit = body_width
    lines.append(current)
    return lines


def _emit_client_init_stub() -> list[str]:
    """``Client.__init__`` signature and docstring from runtime ``client_surface.Client``."""
    sig = inspect.signature(RuntimeClient.__init__)
    doc = inspect.getdoc(RuntimeClient) or ""
    if doc:
        doc = doc.strip().split("\n\n", maxsplit=1)[0].strip()
    lines: list[str] = ["    def __init__("]
    saw_kwonly = False
    for param in sig.parameters.values():
        if param.name == "self":
            lines.append("        self,")
            continue
        if param.kind == inspect.Parameter.KEYWORD_ONLY and not saw_kwonly:
            lines.append("        *,")
            saw_kwonly = True
        lines.append(_format_init_param(param))
    lines.append("    ) -> None:")
    if doc:
        wrapped = _wrap_doc_text(doc, first_line_width=77, body_width=80)
        if len(wrapped) == 1:
            lines.append(f'        """{wrapped[0].replace(chr(34), chr(39))}"""')
        else:
            lines.append('        """' + wrapped[0])
            for doc_line in wrapped[1:]:
                lines.append(f"        {doc_line}")
            lines.append('        """')
    lines.append("        ...")
    return lines


def _emit_client_wait_until_stub() -> list[str]:
    sig = inspect.signature(RuntimeClient.wait_until)
    lines: list[str] = ["    def wait_until("]
    saw_kwonly = False
    for param in sig.parameters.values():
        if param.name == "self":
            lines.append("        self,")
            continue
        if param.kind == inspect.Parameter.KEYWORD_ONLY and not saw_kwonly:
            lines.append("        *,")
            saw_kwonly = True
        lines.append(_format_init_param(param))
    ret_ann = sig.return_annotation
    ret = ret_ann if isinstance(ret_ann, str) else getattr(ret_ann, "__name__", str(ret_ann))
    doc_para = _first_docstring_paragraph(RuntimeClient.wait_until)
    lines.append(f"    ) -> {ret}:")
    if doc_para:
        lines.append(f'        """{doc_para}"""')
    lines.append("        ...")
    return lines


def _load_facade_contract_resources() -> dict[str, dict[str, Any]]:
    """Load effective (generated + overlay) contract resources keyed by attr_name."""
    try:
        from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    except ImportError as error:
        raise RuntimeError(
            "Missing generated runtime contract module. "
            "Run: uv run python devtools/model_sync.py"
        ) from error

    candidate = RUNTIME_REGISTRY_CONTRACT.get("resources")
    if not isinstance(candidate, list):
        raise RuntimeError(
            "Invalid generated runtime contract: resources must be a list"
        )
    resources = [item for item in candidate if isinstance(item, dict)]

    resources = merge_generated_contract_with_overlay(resources)

    by_attr: dict[str, dict[str, Any]] = {}
    for resource in resources:
        attr_name = resource.get("attr_name")
        if isinstance(attr_name, str):
            by_attr[attr_name] = resource
    if not by_attr:
        raise RuntimeError("Invalid facade contract: resources list is empty")
    # Experimental registry facades are not in the generated runtime contract;
    # synthesize minimal rows so stub generation and validation stay aligned.
    for entry in RESOURCE_REGISTRY:
        if entry.attr_name in by_attr:
            continue
        if entry.attr_name not in EXPERIMENTAL_REGISTRY_ATTR_NAMES:
            continue
        by_attr[entry.attr_name] = {
            "attr_name": entry.attr_name,
            "supported_ops": sorted(entry.supported_ops),
            "canonical_entities": sorted(
                model_sync_entity_for_model(entry.model_class)
            ),
            "description": "",
        }
    return by_attr


def _validate_descriptions_and_model_sync() -> None:
    """Validate description propagation and model-sync coverage for registry models."""
    contract_resources = _load_facade_contract_resources()
    if not RESOURCE_DESCRIPTIONS:
        overlay = _load_description_overlay()
        for entry in RESOURCE_REGISTRY:
            contract_row = contract_resources.get(entry.attr_name, {})
            generated_description = contract_row.get("description")
            generated_str = (
                generated_description.strip()
                if isinstance(generated_description, str)
                and generated_description.strip()
                else ""
            )
            overlay_str = overlay.get(entry.attr_name, "").strip()
            # Curated overlay (devtools/model_sync_profiles/resource_descriptions.json)
            # wins over generated contract text, which is often boilerplate like
            # "X resource model extending BaseResource." and hides API-focused copy.
            if overlay_str:
                description = overlay_str
            elif generated_str:
                description = generated_str
            else:
                description = _default_description_from_attr(entry.attr_name)
            RESOURCE_DESCRIPTIONS[entry.attr_name] = description

    missing_descriptions = sorted(
        entry.attr_name
        for entry in RESOURCE_REGISTRY
        if not RESOURCE_DESCRIPTIONS.get(entry.attr_name, "").strip()
    )
    if missing_descriptions:
        raise RuntimeError(
            "Missing RESOURCE_DESCRIPTIONS entries for: "
            + ", ".join(missing_descriptions)
        )

    missing_contract_resources = sorted(
        entry.attr_name
        for entry in RESOURCE_REGISTRY
        if entry.attr_name not in contract_resources
    )
    if missing_contract_resources:
        raise RuntimeError(
            "Model-sync facade contract missing resources for registry entries: "
            + ", ".join(missing_contract_resources)
        )

    entity_names = _load_model_sync_entities()
    if not entity_names:
        entity_names = set()
        for resource in contract_resources.values():
            canonical = resource.get("canonical_entities")
            if isinstance(canonical, list):
                entity_names.update(
                    value for value in canonical if isinstance(value, str)
                )

    op_mismatches: list[str] = []
    missing_sync_entities = sorted(
        entry.model_class.__name__
        for entry in RESOURCE_REGISTRY
        if entry.attr_name not in EXPERIMENTAL_REGISTRY_ATTR_NAMES
        if not (model_sync_entity_for_model(entry.model_class) & entity_names)
    )
    for entry in RESOURCE_REGISTRY:
        resource = contract_resources[entry.attr_name]
        contract_ops = resource.get("supported_ops")
        if not isinstance(contract_ops, list):
            op_mismatches.append(entry.attr_name)
            continue
        normalized_contract_ops = sorted(
            op for op in contract_ops if isinstance(op, str)
        )
        normalized_registry_ops = sorted(entry.supported_ops)
        if normalized_contract_ops != normalized_registry_ops:
            op_mismatches.append(entry.attr_name)

    if missing_sync_entities:
        raise RuntimeError(
            "Model-sync mapping missing canonical entities for registry models: "
            + ", ".join(missing_sync_entities)
        )
    if op_mismatches:
        raise RuntimeError(
            "Model-sync facade contract has supported_ops mismatches for: "
            + ", ".join(sorted(op_mismatches))
        )


def _build_class_docstring(
    entry: ResourceEntry, contract_row: dict[str, Any]
) -> list[str]:
    """Build multi-line class docstring from description + registry metadata."""
    desc = RESOURCE_DESCRIPTIONS.get(entry.attr_name, "")
    parts: list[str] = []
    if desc:
        parts.append(desc)

    # Identity kwargs — wrap if the line would exceed 88 chars
    if entry.filter_kwarg_map:
        items = [f"{k} (-> {v})" for k, v in entry.filter_kwarg_map.items()]
        id_line = f"Identity kwargs: {', '.join(items)}."
        # 4 chars indent in class body
        if len(id_line) + 4 <= 88:
            parts.append(id_line)
        else:
            # Split across lines
            parts.append("Identity kwargs:")
            for item in items:
                parts.append(f"  {item}")

    # Parent scoping
    if entry.parent_kind:
        parts.append(f"Supports list(parent=<{entry.parent_kind}>).")

    # Scope
    if entry.scope == "oss":
        parts.append("OSS-scoped (namespace fixed to 'oss').")

    create_mode = contract_row.get("create_mode")
    if isinstance(create_mode, str) and create_mode != "unsupported":
        parts.append(f"Create mode: {create_mode}.")
    if contract_row.get("update_requires_mask") is True:
        parts.append("Update mode: update_mask required.")
    workflow_flags = contract_row.get("workflow_flags")
    if isinstance(workflow_flags, list) and workflow_flags:
        normalized_flags = ", ".join(
            flag for flag in workflow_flags if isinstance(flag, str)
        )
        if normalized_flags:
            parts.append(f"Workflow flags: {normalized_flags}.")

    if not parts:
        return ['    """Resource facade."""']

    if len(parts) == 1:
        return [f'    """{parts[0]}"""']

    lines = [f'    """{parts[0]}', ""]
    for p in parts[1:]:
        lines.append(f"    {p}")
    lines.append('    """')
    return lines


def _emit_resource_class(
    entry: ResourceEntry,
    contract_row: dict[str, Any],
) -> list[str]:
    """Generate a per-resource stub class inheriting typed facade bases."""
    model_name = entry.model_class.__name__
    class_name = f"_{model_name}Facade"
    base = _stub_base_class(entry)

    lines: list[str] = []
    lines.append(f"class {class_name}({base}):")
    lines.extend(_build_class_docstring(entry, contract_row))
    create_lines = _emit_create_override(entry, contract_row)
    extra = _stub_extra_methods(entry)
    route_lines = _emit_route_method_stubs(entry)
    list_lines = _emit_list_override(model_name)
    specialized_lines = _emit_specialized_facade_stubs(entry)
    lines.append("")
    lines.extend(list_lines)
    lines.extend(specialized_lines)
    if create_lines:
        lines.append("")
        lines.extend(create_lines)
    for method_name in extra:
        lines.append("")
        lines.extend(_format_method_override(method_name, model_name))
    lines.extend(route_lines)
    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D103
    _validate_descriptions_and_model_sync()
    contract_resources = _load_facade_contract_resources()
    out = src / "endorlabs" / "client_surface.pyi"
    lines: list[str] = [
        "# Generated by devtools/generate_client_stub.py — do not edit by hand.",
        "# pyright: reportImplicitOverride=false",
        "# ruff: noqa: D205",
        "# Source of truth: endorlabs.registry.RESOURCE_REGISTRY"
        " and CUSTOM_FACADE_REGISTRY.",
        "",
        "from collections.abc import Callable",
        "from typing import Any",
        "",
    ]

    # Collect ALL relative imports (alphabetically sorted by module).
    # isort requires one contiguous first-party block in alpha order.
    relative_imports: dict[str, list[str]] = {
        ".api_client": ["APIClient"],
        ".core.filter": ["FilterExpression"],
        ".core.types": ["ListParameters"],
        ".core.whoami": ["WhoamiResult"],
        ".operations.routes": ["RouteResult"],
    }
    facade_imports: set[str] = set()
    custom_attr_names = {c.attr_name for c in CUSTOM_FACADE_REGISTRY}
    for entry in RESOURCE_REGISTRY:
        if entry.attr_name in custom_attr_names:
            continue
        mod = entry.model_class.__module__
        name = entry.model_class.__name__
        if mod.startswith("endorlabs."):
            mod = "." + mod[len("endorlabs.") :]
        if mod not in relative_imports:
            relative_imports[mod] = []
        if name not in relative_imports[mod]:
            relative_imports[mod].append(name)
        contract_row = contract_resources[entry.attr_name]
        if "create" in entry.supported_ops and contract_row.get("create_mode") == "both":
            payload_name = f"Create{name}Payload"
            if payload_name not in relative_imports[mod]:
                relative_imports[mod].append(payload_name)
        base = _stub_base_class(entry)
        specialized = _specialized_facade_name(entry)
        if specialized:
            specialized_imports = relative_imports.setdefault(".facade.specialized", [])
            if specialized not in specialized_imports:
                specialized_imports.append(specialized)
        if base.startswith("ResourceRuntimeFacade"):
            facade_imports.add("ResourceRuntimeFacade")
        elif base.startswith("ListableFacade"):
            facade_imports.add("ListableFacade")
        else:
            facade_imports.add("ResourceRuntimeFacade")
        if _stub_extra_methods(entry):
            facade_imports.add("ResourceRuntimeFacade")
        facade_imports.add("ListableFacade")

    if facade_imports:
        relative_imports[".facade"] = sorted(facade_imports)
    for custom in CUSTOM_FACADE_REGISTRY:
        rel = custom.pyi_import_module.strip()
        if not rel.startswith("."):
            rel = f".{rel}"
        if rel not in relative_imports:
            relative_imports[rel] = []
        if custom.pyi_facade_class not in relative_imports[rel]:
            relative_imports[rel].append(custom.pyi_facade_class)

    for mod in sorted(relative_imports.keys()):
        names = sorted(relative_imports[mod])
        lines.append(f"from {mod} import {', '.join(names)}")

    # -- Per-resource stub classes -----------------------------------------
    # One stub class per model (e.g. EndorLicense + License alias share _EndorLicenseFacade).
    emitted_facade_classes: set[str] = set()
    for entry in RESOURCE_REGISTRY:
        if entry.attr_name in custom_attr_names:
            continue
        model_name = entry.model_class.__name__
        class_name = f"_{model_name}Facade"
        if class_name in emitted_facade_classes:
            continue
        emitted_facade_classes.add(class_name)
        lines.append("")
        lines.extend(_emit_resource_class(entry, contract_resources[entry.attr_name]))

    # -- Client class ------------------------------------------------------
    lines.append("")
    lines.append("class Client:")

    # Build compact resource list for the Client docstring
    resource_names = sorted(e.attr_name for e in RESOURCE_REGISTRY)
    custom_names = [e.attr_name for e in CUSTOM_FACADE_REGISTRY]
    # Wrap resource names into lines of ~78 chars (88 - 4 indent - 6 margin)
    resource_lines: list[str] = []
    current_line = "    "
    for i, name in enumerate(resource_names):
        separator = ", " if i > 0 else ""
        candidate = current_line + separator + name
        if len(candidate) > 78 and current_line.strip():
            resource_lines.append(current_line.rstrip() + ",")
            current_line = "    " + name
        else:
            current_line = candidate
    if current_line.strip():
        resource_lines.append(current_line)

    lines.append('    """Resource-oriented client with typed facades.')
    lines.append("")
    lines.append("    Resources:")
    for rl in resource_lines:
        lines.append(rl)
    if custom_names:
        lines.append(f"    Custom: {', '.join(custom_names)}")
    lines.append('    """')
    lines.append("")
    custom_attr_names = {c.attr_name for c in CUSTOM_FACADE_REGISTRY}
    for entry in RESOURCE_REGISTRY:
        attr = entry.attr_name
        if attr in custom_attr_names:
            continue
        model_name = entry.model_class.__name__
        class_name = f"_{model_name}Facade"
        lines.append(f"    {attr}: {class_name}")
    for custom in CUSTOM_FACADE_REGISTRY:
        lines.append(f"    {custom.attr_name}: {custom.pyi_facade_class}")
    lines.append("")
    lines.append("    _client: APIClient | None")
    lines.append("")
    lines.extend(_emit_client_init_stub())
    lines.append("    def close(self) -> None: ...")
    lines.append("    def __enter__(self) -> Client: ...")
    lines.append("    def __exit__(")
    lines.append("        self,")
    lines.append("        exc_type: type[BaseException] | None,")
    lines.append("        exc_val: BaseException | None,")
    lines.append("        exc_tb: Any,")
    lines.append("    ) -> None: ...")
    lines.append("    def whoami(self) -> WhoamiResult:")
    lines.append(
        '        """Return identity and optional bearer session metadata."""'
    )
    lines.append("        ...")
    lines.extend(_emit_client_wait_until_stub())

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run(
        ["uv", "run", "ruff", "format", str(out)],
        cwd=repo_root,
        check=True,
    )
    logger.info("Wrote %s (%s lines)", out, len(lines))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
