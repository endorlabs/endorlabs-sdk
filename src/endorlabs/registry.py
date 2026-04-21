"""Resource registry for the Client facade.

Runtime entries are adapted from the generated runtime contract and a minimal
manual overlay for intentional SDK divergences.
"""
# ruff: noqa: C901, PERF401, PERF403

from __future__ import annotations

import importlib
from collections.abc import Callable
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
    scope: Literal["oss"] | None = None
    create_mode: Literal["both"] | Literal["payload-only"] | Literal["unsupported"] = (
        "unsupported"
    )
    update_requires_mask: bool = False
    workflow_flags: frozenset[str] = frozenset()


@dataclass
class CustomFacadeEntry:
    """Custom facade on Client; ``factory(client, default_namespace) -> facade``.

    ``pyi_*`` fields are consumed only by ``scripts/generate_client_stub.py`` so
    ``client_surface.pyi`` lists concrete facade types without hardcoding names in
    the generator. They are not used at runtime.

    Use this for SDK-only helpers that are not OpenAPI resources (no row in
    ``registry_contract``), similar to ``ScanLogs`` vs ``ScanLogRequest``.
    """

    attr_name: str
    factory: Callable[["APIClient", str | None], Any]  # noqa: UP037
    pyi_facade_class: str
    pyi_import_module: str
    pyi_attr_doc: str


def _scan_logs_facade(client: APIClient, default_namespace: str | None) -> Any:
    """Build ScanLogsFacade for ``client.ScanLogs`` (request-based log lines API)."""
    from .facade import ScanLogsFacade

    return ScanLogsFacade(client, default_namespace)


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
            "Run: uv run python scripts/model_sync.py"
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
        scope = cast("Literal['oss'] | None", None)
        if scope_value == "oss":
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
            )
        )
    return registry


RESOURCE_REGISTRY: list[ResourceEntry] = _build_resource_registry()

# ``ScanLogs`` is an SDK-only facade (fetch log lines for a scan result). It is not
# an endorctl ``--resource`` kind; CRUD for scan log *requests* uses
# ``client.ScanLogRequest`` like endorctl.
CUSTOM_FACADE_REGISTRY: list[CustomFacadeEntry] = [
    CustomFacadeEntry(
        attr_name="ScanLogs",
        factory=_scan_logs_facade,
        pyi_facade_class="ScanLogsFacade",
        pyi_import_module="facade",
        pyi_attr_doc="Scan logs facade. Use get_logs() to fetch log messages.",
    ),
]
