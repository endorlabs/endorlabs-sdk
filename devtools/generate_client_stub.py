"""Generate Client stub (.pyi) from RESOURCE_REGISTRY and CUSTOM_FACADE_REGISTRY.

Single source of truth: the registry. Run from repo root with:
  uv run python devtools/generate_client_stub.py
Writes src/endorlabs/client_surface.pyi so Pyright types client.Project, etc.

Each resource gets a dedicated stub class (e.g. ``_ProjectFacade``) that
exposes only the methods the resource actually supports, with concrete
return types and validated resource descriptions.
"""
# ruff: noqa: E402, I001, C901, E501, PERF401, PERF402

from __future__ import annotations

import inspect
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Add src so we can import endorlabs.registry
repo_root = Path(__file__).resolve().parent.parent
src = repo_root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from endorlabs.facade import ResourceRuntimeFacade, _ListableFacade
from endorlabs.registry_overlay import merge_generated_contract_with_overlay
from endorlabs.registry import (
    CUSTOM_FACADE_REGISTRY,
    EXPERIMENTAL_REGISTRY_ATTR_NAMES,
    RESOURCE_REGISTRY,
    ResourceEntry,
)
from endorlabs.utils.model_validation import get_tags_update_paths
from sync.policy import model_sync_entity_for_model

logger = logging.getLogger(__name__)


MODEL_SYNC_MAPPING_PATH = (
    repo_root
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "mapping"
    / "entity_mapping.json"
)
RESOURCE_DESCRIPTION_OVERLAY_PATH = (
    repo_root / "scripts" / "model_sync_profiles" / "resource_descriptions.json"
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
# Signature helpers
# ---------------------------------------------------------------------------

# Methods defined on _ListableFacade (always present when "list" is supported)
_LISTABLE_METHODS = ("list", "lookup", "list_iter")
# Methods defined on ResourceRuntimeFacade
_CRUD_METHODS = ("get", "create", "update", "delete")
_TAG_METHODS = ("tag", "untag")

# Map method name -> class that defines it
_METHOD_SOURCE: dict[str, type] = {}
for _m in _LISTABLE_METHODS:
    _METHOD_SOURCE[_m] = _ListableFacade
for _m in (*_CRUD_METHODS, *_TAG_METHODS):
    _METHOD_SOURCE[_m] = ResourceRuntimeFacade


def _get_method_signatures() -> dict[str, inspect.Signature]:
    """Extract signatures for all public facade methods once."""
    sigs: dict[str, inspect.Signature] = {}
    for name, cls in _METHOD_SOURCE.items():
        sigs[name] = inspect.signature(getattr(cls, name))
    return sigs


def _get_method_docline(name: str) -> str:
    """Extract first line of a facade method's docstring.

    Truncates to fit within 88-char line limit (8 chars indent + quotes).
    """
    cls = _METHOD_SOURCE[name]
    doc = getattr(cls, name).__doc__ or ""
    first = doc.strip().split("\n")[0].strip()
    # Method docstrings are indented 8 chars: '        """..."""'
    max_content = 88 - 8 - 6  # 74 chars for the docstring content
    if len(first) > max_content:
        # Truncate at last word boundary that fits
        truncated = first[:max_content].rsplit(" ", 1)[0].rstrip(".,;:")
        first = truncated + "."
    return first


def _format_annotation(ann: Any, model_name: str) -> str:
    """Convert an inspect annotation to a .pyi string, replacing T."""
    if ann is inspect.Parameter.empty:
        return ""
    s = str(ann) if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
    # Replace the generic type variable T with the concrete model name.
    # Use word-boundary replacement so e.g. "Iterator" is not mangled.
    s = re.sub(r"\bT\b", model_name, s)
    return s


def _format_default(default: Any) -> str:
    """Convert inspect default to .pyi representation."""
    if default is inspect.Parameter.empty:
        return ""
    # In .pyi stubs, all defaults are represented as ...
    return " = ..."


def _format_method(
    name: str,
    sig: inspect.Signature,
    model_name: str,
    indent: str = "    ",
) -> list[str]:
    """Format one method as .pyi stub lines."""
    docline = _get_method_docline(name)
    params: list[str] = []
    saw_keyword_only = False

    for pname, param in sig.parameters.items():
        if pname == "self":
            params.append(f"{indent}    self,")
            continue

        # Insert bare * for keyword-only boundary
        if param.kind == inspect.Parameter.KEYWORD_ONLY and not saw_keyword_only:
            params.append(f"{indent}    *,")
            saw_keyword_only = True

        ann = _format_annotation(param.annotation, model_name)
        default = _format_default(param.default)
        ann_str = f": {ann}" if ann else ""

        if param.kind == inspect.Parameter.VAR_KEYWORD:
            params.append(f"{indent}    **{pname}{ann_str},")
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            params.append(f"{indent}    *{pname}{ann_str},")
        else:
            params.append(f"{indent}    {pname}{ann_str}{default},")

    ret = _format_annotation(sig.return_annotation, model_name)
    ret_str = f" -> {ret}" if ret else ""

    lines = [f"{indent}def {name}("]
    lines.extend(params)
    lines.append(f"{indent}){ret_str}:")
    if docline:
        lines.append(f'{indent}    """{docline}"""')
    lines.append(f"{indent}    ...")
    return lines


# ---------------------------------------------------------------------------
# Per-resource class builder
# ---------------------------------------------------------------------------


def _get_available_methods(entry: ResourceEntry) -> list[str]:
    """Return method names this resource supports."""
    methods: list[str] = []
    if "list" in entry.supported_ops:
        methods.extend(_LISTABLE_METHODS)
    if "get" in entry.supported_ops:
        methods.append("get")
    if "create" in entry.supported_ops:
        methods.append("create")
    if "update" in entry.supported_ops:
        methods.append("update")
    if "delete" in entry.supported_ops:
        methods.append("delete")
    if "update" in entry.supported_ops:
        tags_paths = get_tags_update_paths(entry.model_class)
        if "meta.tags" in tags_paths:
            methods.extend(_TAG_METHODS)
    return methods


def _load_model_sync_entities() -> set[str]:
    """Load canonical model-sync entity names when available."""
    if not MODEL_SYNC_MAPPING_PATH.exists():
        return set()
    payload = json.loads(MODEL_SYNC_MAPPING_PATH.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return set()
    entity_names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entity_name = entry.get("entity_name")
        if isinstance(entity_name, str):
            entity_names.add(entity_name)
    return entity_names


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
        raise RuntimeError("Invalid generated runtime contract: resources must be a list")
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
                entity_names.update(value for value in canonical if isinstance(value, str))

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
        normalized_contract_ops = sorted(op for op in contract_ops if isinstance(op, str))
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


def _build_class_docstring(entry: ResourceEntry, contract_row: dict[str, Any]) -> list[str]:
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
    sigs: dict[str, inspect.Signature],
) -> list[str]:
    """Generate a per-resource stub class."""
    model_name = entry.model_class.__name__
    # Class name: _ProjectFacade, _FindingFacade, etc.
    class_name = f"_{model_name}Facade"
    methods = _get_available_methods(entry)

    lines: list[str] = []
    lines.append(f"class {class_name}:")
    lines.extend(_build_class_docstring(entry, contract_row))
    lines.append("")

    for i, method_name in enumerate(methods):
        sig = sigs[method_name]
        lines.extend(_format_method(method_name, sig, model_name))
        # Blank line between methods, but not after the last one
        if i < len(methods) - 1:
            lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D103
    _validate_descriptions_and_model_sync()
    contract_resources = _load_facade_contract_resources()
    out = src / "endorlabs" / "client_surface.pyi"
    sigs = _get_method_signatures()

    lines: list[str] = [
        "# Generated by devtools/generate_client_stub.py — do not edit by hand.",
        "# Source of truth: endorlabs.registry.RESOURCE_REGISTRY"
        " and CUSTOM_FACADE_REGISTRY.",
        "",
        "from collections.abc import Iterator",
        "from typing import Any",
        "",
    ]

    # Collect ALL relative imports (alphabetically sorted by module).
    # isort requires one contiguous first-party block in alpha order.
    relative_imports: dict[str, list[str]] = {
        ".api_client": ["APIClient"],
        ".core.filter": ["FilterExpression"],
        ".core.types": ["ListParameters"],
    }
    for entry in RESOURCE_REGISTRY:
        mod = entry.model_class.__module__
        name = entry.model_class.__name__
        if mod.startswith("endorlabs."):
            mod = "." + mod[len("endorlabs.") :]
        if mod not in relative_imports:
            relative_imports[mod] = []
        if name not in relative_imports[mod]:
            relative_imports[mod].append(name)

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
        model_name = entry.model_class.__name__
        class_name = f"_{model_name}Facade"
        if class_name in emitted_facade_classes:
            continue
        emitted_facade_classes.add(class_name)
        lines.append("")
        lines.extend(_emit_resource_class(entry, contract_resources[entry.attr_name], sigs))

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
    for entry in RESOURCE_REGISTRY:
        attr = entry.attr_name
        model_name = entry.model_class.__name__
        class_name = f"_{model_name}Facade"
        desc = RESOURCE_DESCRIPTIONS.get(attr, "")
        lines.append(f"    {attr}: {class_name}")
        if desc:
            lines.append(f'    """{desc}"""')
    for custom in CUSTOM_FACADE_REGISTRY:
        lines.append(f"    {custom.attr_name}: {custom.pyi_facade_class}")
        if custom.pyi_attr_doc:
            lines.append(f'    """{custom.pyi_attr_doc}"""')
    lines.append("")
    lines.append("    _client: APIClient | None")
    lines.append("")
    lines.append("    def __init__(")
    lines.append("        self,")
    lines.append("        api_client: APIClient | None = ...,")
    lines.append("        tenant: str | None = ...,")
    lines.append("        *,")
    lines.append("        timeout: float = ...,")
    lines.append("        content_type: str = ...,")
    lines.append("        accept_encoding: str | None = ...,")
    lines.append("        max_retries: int = ...,")
    lines.append("        base_url: str | None = ...,")
    lines.append("        **client_kwargs: Any,")
    lines.append("    ) -> None: ...")
    lines.append("    def close(self) -> None: ...")
    lines.append("    def __enter__(self) -> Client: ...")
    lines.append("    def __exit__(")
    lines.append("        self,")
    lines.append("        exc_type: type[BaseException] | None,")
    lines.append("        exc_val: BaseException | None,")
    lines.append("        exc_tb: Any,")
    lines.append("    ) -> None: ...")
    lines.append("    def whoami(self) -> str | None:")
    lines.append('        """Return the authenticated identity name, or None."""')
    lines.append("        ...")
    lines.append("    def wait_until(")
    lines.append("        self,")
    lines.append("        predicate: Any,")
    lines.append("        timeout: float = ...,")
    lines.append("        poll_interval_max: float = ...,")
    lines.append("    ) -> bool: ...")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Wrote %s (%s lines)", out, len(lines))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
