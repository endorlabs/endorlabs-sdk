"""Resource registry for the Client facade.

Runtime entries are adapted from the generated runtime contract and a minimal
manual overlay for intentional SDK divergences.
"""
# ruff: noqa: C901, PERF401, PERF403

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from .api_client import APIClient

from .registry_overlay import merge_generated_contract_with_overlay


@dataclass
class ResourceEntry:
    """One resource exposed on Client; used to build facade in __init__."""

    attr_name: str
    resource_name: str
    model_class: type
    supported_ops: frozenset[str] = frozenset(
        {"list", "get", "create", "update", "delete"}
    )
    build_create_payload_fn: Callable[..., Any] | None = None
    filter_kwarg_map: dict[str, str] = field(default_factory=dict)  # pyright: ignore[reportUnknownVariableType]
    parent_kind: str | None = None
    scope: Literal["system"] | Literal["oss"] | None = None
    create_mode: Literal["both"] | Literal["payload-only"] | Literal["unsupported"] = (
        "unsupported"
    )
    update_requires_mask: bool = False
    workflow_flags: frozenset[str] = frozenset()
    create_convenience_spec_fields: tuple[str, ...] = ()
    create_convenience_spec_required: tuple[str, ...] = ()
    create_convenience_meta_fields: tuple[str, ...] = ()
    create_convenience_payload_top_level_fields: tuple[str, ...] = ()
    create_convenience_read_only_spec_fields: tuple[str, ...] = ()
    convenience_skip_reason: str | None = None


@dataclass
class CustomFacadeEntry:
    """Custom facade on Client; ``factory(client, default_namespace) -> facade``.

    ``pyi_*`` fields are consumed only by ``devtools/generate_client_stub.py`` so
    ``client_surface.pyi`` lists concrete facade types without hardcoding names in
    the generator. They are not used at runtime.

    Use this for SDK-only helpers that are not OpenAPI resources (no row in
    ``registry_contract``), e.g. ``CallGraphData`` decode/fetch until registry
    list/get is wired.
    """

    attr_name: str
    factory: Callable[[APIClient, str | None], Any]
    pyi_facade_class: str
    pyi_import_module: str
    pyi_attr_doc: str


def _call_graph_data_facade(client: APIClient, default_namespace: str | None) -> Any:
    """Build CallGraphDataFacade for ``client.CallGraphData``."""
    from .facade import CallGraphDataFacade

    return CallGraphDataFacade(client, default_namespace)


def _normalize_contract_rows(items: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in items:
        if isinstance(entry, dict):
            rows.append(cast("dict[str, Any]", entry))
    return rows


def _load_generated_runtime_contract() -> list[dict[str, Any]]:
    try:
        from .generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    except Exception as error:
        raise RuntimeError(
            "Missing generated runtime registry contract. "
            "Run: uv run python devtools/model_sync.py"
        ) from error
    runtime_contract = cast("dict[str, Any]", RUNTIME_REGISTRY_CONTRACT)
    resources_any = runtime_contract.get("resources")
    if not isinstance(resources_any, list):
        raise TypeError(
            "Invalid generated runtime registry contract: resources must be a list"
        )
    normalized = _normalize_contract_rows(cast("list[Any]", resources_any))
    return sorted(normalized, key=lambda item: str(item.get("attr_name", "")))


def _load_symbol(import_path: str) -> Any:
    module_name, _, symbol_name = import_path.partition(":")
    if not module_name or not symbol_name:
        raise RuntimeError(f"Invalid import path in generated contract: {import_path}")
    module = importlib.import_module(module_name)
    try:
        return getattr(module, symbol_name)
    except AttributeError as error:
        raise RuntimeError(
            f"Missing symbol from generated contract import path: {import_path}"
        ) from error


def _build_resource_registry() -> list[ResourceEntry]:
    effective_contract = merge_generated_contract_with_overlay(
        _load_generated_runtime_contract()
    )
    registry: list[ResourceEntry] = []
    for item in effective_contract:
        attr_name = item.get("attr_name")
        resource_name = item.get("resource_name")
        model_class_name = item.get("model_class")
        if not isinstance(attr_name, str) or not isinstance(resource_name, str):
            continue
        if not isinstance(model_class_name, str):
            continue
        model_class_import_path = item.get("model_class_import_path")
        if not isinstance(model_class_import_path, str):
            raise TypeError(
                f"Missing model_class_import_path for resource '{attr_name}'"
            )
        loaded_model = _load_symbol(model_class_import_path)
        if not isinstance(loaded_model, type):
            raise TypeError(
                "Model import path did not resolve to a class: "
                f"{model_class_import_path}"
            )
        model_class = loaded_model
        supported_ops_value = item.get("supported_ops")
        supported_ops: frozenset[str] = frozenset(
            {"list", "get", "create", "update", "delete"}
        )
        if isinstance(supported_ops_value, list):
            normalized_ops: set[str] = set()
            for op in cast("list[Any]", supported_ops_value):
                if isinstance(op, str):
                    normalized_ops.add(op)
            supported_ops = frozenset(normalized_ops)
        filter_kwarg_map_value = item.get("filter_kwarg_map")
        filter_kwarg_map: dict[str, str] = {}
        if isinstance(filter_kwarg_map_value, dict):
            for key, value in cast("dict[Any, Any]", filter_kwarg_map_value).items():
                if isinstance(key, str) and isinstance(value, str):
                    filter_kwarg_map[key] = value
        build_create_payload_fn_name = item.get("build_create_payload_fn_name")
        build_create_payload_fn_import_path = item.get(
            "build_create_payload_fn_import_path"
        )
        build_create_payload_fn: Callable[..., Any] | None = None
        if isinstance(build_create_payload_fn_import_path, str):
            loaded_builder = _load_symbol(build_create_payload_fn_import_path)
            if not callable(loaded_builder):
                raise TypeError(
                    "Create builder import path did not resolve to callable: "
                    f"{build_create_payload_fn_import_path}"
                )
            build_create_payload_fn = loaded_builder
        elif isinstance(build_create_payload_fn_name, str):
            raise TypeError(
                "Missing build_create_payload_fn_import_path "
                f"for resource '{attr_name}'"
            )
        scope_value = item.get("scope")
        scope = cast("Literal['system'] | Literal['oss'] | None", None)
        if scope_value in {"system", "oss"}:
            scope = scope_value
        parent_kind_value = item.get("parent_kind")
        parent_kind = parent_kind_value if isinstance(parent_kind_value, str) else None
        create_mode_value = item.get("create_mode")
        create_mode: (
            Literal["both"] | Literal["payload-only"] | Literal["unsupported"]
        ) = "unsupported"
        if create_mode_value in {"both", "payload-only", "unsupported"}:
            create_mode = create_mode_value
        update_requires_mask = bool(item.get("update_requires_mask"))
        workflow_flags_value = item.get("workflow_flags")
        workflow_flag_candidates: list[object] = (
            cast("list[object]", workflow_flags_value)
            if isinstance(workflow_flags_value, list)
            else []
        )
        workflow_flags: frozenset[str] = frozenset(
            value for value in workflow_flag_candidates if isinstance(value, str)
        )

        def _str_tuple(key: str, row: dict[str, Any] = item) -> tuple[str, ...]:
            raw = row.get(key)
            if not isinstance(raw, list):
                return ()
            names: list[str] = []
            for value in cast("list[Any]", raw):
                if isinstance(value, str):
                    names.append(value)
            return tuple(names)

        skip_raw = item.get("convenience_skip_reason")
        convenience_skip_reason = skip_raw if isinstance(skip_raw, str) else None

        registry.append(
            ResourceEntry(
                attr_name=attr_name,
                resource_name=resource_name,
                model_class=model_class,
                supported_ops=supported_ops,
                build_create_payload_fn=build_create_payload_fn,
                filter_kwarg_map=filter_kwarg_map,
                parent_kind=parent_kind,
                scope=scope,
                create_mode=create_mode,
                update_requires_mask=update_requires_mask,
                workflow_flags=workflow_flags,
                create_convenience_spec_fields=_str_tuple(
                    "create_convenience_spec_fields"
                ),
                create_convenience_spec_required=_str_tuple(
                    "create_convenience_spec_required"
                ),
                create_convenience_meta_fields=_str_tuple(
                    "create_convenience_meta_fields"
                ),
                create_convenience_payload_top_level_fields=_str_tuple(
                    "create_convenience_payload_top_level_fields"
                ),
                create_convenience_read_only_spec_fields=_str_tuple(
                    "create_convenience_read_only_spec_fields"
                ),
                convenience_skip_reason=convenience_skip_reason,
            )
        )
    return registry


def _normalize_experimental_supported_ops(value: Any) -> frozenset[str]:
    """Default list/get; accept set, frozenset, list, tuple, or single str."""
    if value is None:
        return frozenset({"list", "get"})
    if isinstance(value, (frozenset, set)):
        return frozenset(str(x) for x in cast("Iterable[object]", value))
    if isinstance(value, (list, tuple)):
        return frozenset(str(x) for x in cast("Iterable[object]", value))
    if isinstance(value, str):
        return frozenset({value})
    return frozenset({"list", "get"})


# Facades appended to the generated runtime contract (see ``_build_resource_registry``).
EXPERIMENTAL_RESOURCE_SPECS: list[dict[str, Any]] = [
    {
        "attr_name": "VectorStore",
        "resource_name": "vector-stores",
        "model_import_path": "endorlabs.resources.vector_store:VectorStore",
        "filter_kwarg_map": {"name": "meta.name"},
    },
    {
        "attr_name": "VectorStoreQuery",
        "resource_name": "queries/vector-stores",
        "model_import_path": "endorlabs.resources.vector_store_query:VectorStoreQuery",
        "supported_ops": frozenset({"create"}),
        "create_mode": "both",
        "build_create_payload_fn_import_path": (
            "endorlabs.resources.vector_store_query:build_create_payload"
        ),
    },
]

EXPERIMENTAL_REGISTRY_ATTR_NAMES: frozenset[str] = frozenset(
    str(s["attr_name"])
    for s in EXPERIMENTAL_RESOURCE_SPECS
    if isinstance(s.get("attr_name"), str)
)


def _build_generated_experimental_facades() -> list[ResourceEntry]:
    """Build additional generated-model facades not yet in runtime contract.

    These facades are intentionally lightweight and primarily support read/list
    experimentation for newly exposed API resources.
    """
    specs = EXPERIMENTAL_RESOURCE_SPECS

    primary_registry = _build_resource_registry()
    existing = {entry.attr_name for entry in primary_registry}
    existing_model_classes = {entry.model_class for entry in primary_registry}
    entries: list[ResourceEntry] = []
    for spec in specs:
        attr_name = spec["attr_name"]
        if not isinstance(attr_name, str):
            continue
        if attr_name in existing:
            continue
        model_import_path = spec.get("model_import_path")
        if not isinstance(model_import_path, str):
            continue
        loaded_model = _load_symbol(model_import_path)
        if not isinstance(loaded_model, type):
            continue
        if loaded_model in existing_model_classes:
            # Contract/stub tooling keys facade rows by model-class name; skip
            # experimental aliases that would duplicate existing modeled rows.
            continue
        supported_ops = _normalize_experimental_supported_ops(spec.get("supported_ops"))
        scope_value = spec.get("scope")
        scope = cast("Literal['system'] | Literal['oss'] | None", None)
        if scope_value in {"system", "oss"}:
            scope = scope_value
        create_mode_value = spec.get("create_mode")
        create_mode: (
            Literal["both"] | Literal["payload-only"] | Literal["unsupported"]
        ) = "unsupported"
        if create_mode_value in {"both", "payload-only", "unsupported"}:
            create_mode = create_mode_value
        build_path = spec.get("build_create_payload_fn_import_path")
        build_create_payload_fn: Callable[..., Any] | None = None
        if isinstance(build_path, str):
            loaded_builder = _load_symbol(build_path)
            if not callable(loaded_builder):
                raise TypeError(
                    "Experimental build_create_payload import path did not resolve "
                    f"to callable: {build_path}"
                )
            build_create_payload_fn = loaded_builder
        resource_name = spec.get("resource_name")
        if not isinstance(resource_name, str):
            continue
        filter_kwarg_map: dict[str, str] = {}
        fkm = spec.get("filter_kwarg_map")
        if isinstance(fkm, dict):
            for key, val in cast("dict[str, Any]", fkm).items():
                if isinstance(val, str):
                    filter_kwarg_map[key] = val
        entries.append(
            ResourceEntry(
                attr_name=attr_name,
                resource_name=resource_name,
                model_class=loaded_model,
                supported_ops=supported_ops,
                build_create_payload_fn=build_create_payload_fn,
                filter_kwarg_map=filter_kwarg_map,
                scope=scope,
                create_mode=create_mode,
            )
        )
    return entries


_PRIMARY_RESOURCE_REGISTRY = _build_resource_registry()
RESOURCE_REGISTRY: list[ResourceEntry] = _PRIMARY_RESOURCE_REGISTRY + (
    _build_generated_experimental_facades()
)

# ``CallGraphData`` is an SDK custom facade (decode/fetch by parent PackageVersion).
# Log lines use ``ScanResult.get_logs`` (ScanLogRequest wire API). CRUD for scan
# log *requests* uses ``client.ScanLogRequest`` like endorctl.
CUSTOM_FACADE_REGISTRY: list[CustomFacadeEntry] = [
    CustomFacadeEntry(
        attr_name="CallGraphData",
        factory=_call_graph_data_facade,
        pyi_facade_class="CallGraphDataFacade",
        pyi_import_module="facade",
        pyi_attr_doc=(
            "Call graph data facade. Use decode() or fetch() with a PackageVersion."
        ),
    ),
]
