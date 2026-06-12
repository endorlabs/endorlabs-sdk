"""Generate reference docs from SDK registry/facades and OpenAPI spec.

Run from repo root:
    uv run python devtools/generate_reference_docs.py
"""

from __future__ import annotations

import argparse
import inspect
import json
import logging
import sys
from pathlib import Path
from typing import Any, get_args, get_origin

import httpx
from sync.path_safety import find_repo_root, safe_repo_output_path

REPO_ROOT = find_repo_root(start=Path(__file__).resolve().parent)
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
DEVTOOLS_DIR = REPO_ROOT / "devtools"
if str(DEVTOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(DEVTOOLS_DIR))

import endorlabs  # noqa: E402
from endorlabs import resources as resource_modules  # noqa: E402
from endorlabs.facade import ResourceRuntimeFacade, _ListableFacade  # noqa: E402
from endorlabs.registry import RESOURCE_REGISTRY  # noqa: E402

logger = logging.getLogger(__name__)

SPEC_PATH = (
    REPO_ROOT / ".endorlabs-context" / "platform" / "openapi" / "openapiv2.swagger.json"
)
SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"
REGISTRY_CONTRACT_PATH = (
    REPO_ROOT / "src" / "endorlabs" / "generated" / "registry_contract.py"
)

GENERATED_REFERENCE_DIR = safe_repo_output_path(
    REPO_ROOT, "docs", "generated-reference"
)
RESOURCES_DOC = GENERATED_REFERENCE_DIR / "resources.md"
PAYLOADS_DOC = GENERATED_REFERENCE_DIR / "create-update-payloads.md"
SURFACES_DOC = GENERATED_REFERENCE_DIR / "api-surfaces.md"
COVERAGE_JSON = GENERATED_REFERENCE_DIR / "coverage.json"

SDK_OP_ORDER = ("list", "get", "create", "update", "delete")

RESOURCE_LIMITATIONS: dict[str, str] = {
    "project": "Platform-managed",
    "repository": "Platform-managed",
    "repository_version": "Platform-managed",
    "package_version": "Scan-discovered; API may return 501 for PATCH",
    "finding": "Scan-generated",
    "scan_result": "Scan-generated",
    "policy": "Rego in payload",
    "installation": "Platform-managed",
    "metric": "Analytics-generated",
    "dependency_metadata": "OSS namespace; relationship resource",
    "linter_result": "Scan-generated",
    "scan_log_request": "Request-based only; no list/get/delete for log messages",
    "scan_workflow": "Platform-managed",
    "scan_workflow_result": "Platform-managed",
    "version_upgrade": "Platform-managed",
    "authentication_log": "Tenant-context read-only resource",
    "endor_license": "Tenant-context read-only resource",
    "policy_template": "Tenant-context read-only resource",
    "vulnerability": "OSS-scoped vulnerability dataset",
    "malware": "OSS-scoped malware dataset",
    "query_vulnerability": "Request-based query endpoint (create only)",
    "query_malware": "Request-based query endpoint (create only)",
}


def _load_spec() -> dict[str, Any]:
    if SPEC_PATH.exists():
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    response = httpx.get(SPEC_URL, timeout=60)
    response.raise_for_status()
    return response.json()


def _bool_cell(value: bool) -> str:
    return "yes" if value else "no"


def _load_runtime_registry_contract() -> dict[str, Any]:
    try:
        from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    except ImportError:
        return {}
    if isinstance(RUNTIME_REGISTRY_CONTRACT, dict):
        return RUNTIME_REGISTRY_CONTRACT
    return {}


def _canonical_entity_count(contract: dict[str, Any]) -> int:
    resources = contract.get("resources")
    if not isinstance(resources, list):
        return 0
    entities: set[str] = set()
    for row in resources:
        if not isinstance(row, dict):
            continue
        canonical = row.get("canonical_entities")
        if isinstance(canonical, list):
            entities.update(value for value in canonical if isinstance(value, str))
    return len(entities)


def _model_sync_summary() -> str:
    """Return canonical model-sync summary for doc propagation."""
    contract = _load_runtime_registry_contract()
    if not contract:
        return "Model sync contract: unavailable."
    resource_count = contract.get("resource_count")
    entity_count = _canonical_entity_count(contract)
    contract_path = REGISTRY_CONTRACT_PATH.relative_to(REPO_ROOT).as_posix()
    return (
        f"Model sync contract: `{contract_path}` "
        f"({resource_count} resources, {entity_count} canonical entities)."
    )


def _model_sync_coverage_lines() -> list[str]:
    """Return model-sync coverage lines sourced from the committed runtime contract."""
    contract = _load_runtime_registry_contract()
    if not contract:
        return [
            "## Model-sync coverage snapshot",
            "",
            "- runtime registry contract: unavailable",
            "",
        ]
    resources = contract.get("resources")
    resource_count = (
        len(resources)
        if isinstance(resources, list)
        else contract.get("resource_count")
    )
    entity_count = _canonical_entity_count(contract)
    return [
        "## Model-sync coverage snapshot",
        "",
        f"- facade contract resources: `{resource_count}`",
        f"- canonical entities (union): `{entity_count}`",
        "",
    ]


def _sig_summary(fn: Any | None) -> str:
    if fn is None:
        return "N/A"
    sig = inspect.signature(fn)
    required: list[str] = []
    optional: list[str] = []
    for param in sig.parameters.values():
        if param.name in {"self", "cls"}:
            continue
        if param.default is inspect.Parameter.empty:
            required.append(param.name)
        else:
            optional.append(param.name)
    parts: list[str] = []
    if required:
        parts.append(f"required: {', '.join(required)}")
    if optional:
        parts.append(f"optional: {', '.join(optional)}")
    return "; ".join(parts) if parts else "none"


def _resolve_payload_model_from_builder(
    builder: Any | None,
) -> tuple[str, type[Any] | None]:
    """Resolve create payload model class from builder return annotation."""
    if builder is None:
        return ("N/A", None)

    annotation = inspect.signature(builder).return_annotation
    if annotation is inspect.Signature.empty:
        return ("unknown", None)

    resolved = annotation
    if isinstance(resolved, str):
        resolved = builder.__globals__.get(resolved, resolved)

    origin = get_origin(resolved)
    if origin is not None:
        args = [arg for arg in get_args(resolved) if arg is not type(None)]
        if args:
            resolved = args[0]
            if isinstance(resolved, str):
                resolved = builder.__globals__.get(resolved, resolved)

    if isinstance(resolved, type):
        return (resolved.__name__, resolved)

    return (str(annotation), None)


def _payload_field_summary(payload_model: type[Any] | None) -> tuple[str, str]:
    """Return required/optional field summaries from payload model fields."""
    if payload_model is None:
        return ("N/A", "N/A")

    model_fields = getattr(payload_model, "model_fields", None)
    if not isinstance(model_fields, dict):
        return ("dynamic", "dynamic")

    required: list[str] = []
    optional: list[str] = []
    for name, field_info in model_fields.items():
        is_required = bool(getattr(field_info, "is_required", lambda: False)())
        if is_required:
            required.append(name)
        else:
            optional.append(name)
    required_str = ", ".join(sorted(required)) if required else "none"
    optional_str = ", ".join(sorted(optional)) if optional else "none"
    return (required_str, optional_str)


def _spec_support_by_op(spec: dict[str, Any], path_segment: str) -> dict[str, bool]:
    """Return spec operation support by SDK op semantics.

    - list: GET collection path
    - create: POST collection path
    - update: PATCH collection path
    - get: GET item path
    - delete: DELETE item path
    """
    base = f"/v1/namespaces/{{tenant_meta.namespace}}/{path_segment}"
    item = f"{base}/{{uuid}}"
    paths = spec.get("paths", {})
    collection_entry = paths.get(base, {}) if isinstance(paths, dict) else {}
    item_entry = paths.get(item, {}) if isinstance(paths, dict) else {}
    if not isinstance(collection_entry, dict):
        collection_entry = {}
    if not isinstance(item_entry, dict):
        item_entry = {}
    return {
        "list": "get" in collection_entry,
        "create": "post" in collection_entry,
        "update": "patch" in collection_entry,
        "get": "get" in item_entry,
        "delete": "delete" in item_entry,
    }


def _generate_resources_md(spec: dict[str, Any]) -> str:
    lines = [
        "# Resources (SDK API Surface)",
        "",
        "Auto-generated from `src/endorlabs/registry.py` and OpenAPI spec.",
        _model_sync_summary(),
        "Each operation column is `sdk/spec` where spec is derived from OpenAPI",
        "collection and item paths.",
        "",
        "Legend:",
        "- `yes/yes`: SDK operation exists and OpenAPI operation exists.",
        "- `no/yes`: API supports it, SDK intentionally does not expose it on",
        "  the facade.",
        "- `yes/no`: SDK exposes operation but collection/item OpenAPI",
        "  method was not found.",
        "- `no/no`: operation not exposed by SDK and not present in OpenAPI paths.",
        "- Scope values: `tenant` (default namespace resolution), `oss`",
        "  (namespace fixed to `oss`).",
        "",
        "| Resource | List (sdk/spec) | Get (sdk/spec) | Create (sdk/spec) | "
        "Update (sdk/spec) | Delete (sdk/spec) | Scope | Parent | Limitations |",
        "|----------|------------------|----------------|-------------------|-------------------|-------------------|-------|--------|-------------|",
    ]
    lines.extend(_model_sync_coverage_lines())
    for entry in sorted(RESOURCE_REGISTRY, key=lambda e: e.attr_name):
        spec_support = _spec_support_by_op(spec, entry.resource_name)
        limitations = RESOURCE_LIMITATIONS.get(entry.attr_name, "—")
        list_pair = (
            f"{_bool_cell('list' in entry.supported_ops)}"
            f"/{_bool_cell(spec_support['list'])}"
        )
        get_pair = (
            f"{_bool_cell('get' in entry.supported_ops)}"
            f"/{_bool_cell(spec_support['get'])}"
        )
        create_pair = (
            f"{_bool_cell('create' in entry.supported_ops)}"
            f"/{_bool_cell(spec_support['create'])}"
        )
        update_pair = (
            f"{_bool_cell('update' in entry.supported_ops)}"
            f"/{_bool_cell(spec_support['update'])}"
        )
        delete_pair = (
            f"{_bool_cell('delete' in entry.supported_ops)}"
            f"/{_bool_cell(spec_support['delete'])}"
        )
        lines.append(
            "| "
            f"{entry.attr_name} | "
            f"{list_pair} | "
            f"{get_pair} | "
            f"{create_pair} | "
            f"{update_pair} | "
            f"{delete_pair} | "
            f"{entry.scope or 'tenant'} | "
            f"{entry.parent_kind or '—'} | "
            f"{limitations} |"
        )
    lines.extend(
        [
            "",
            f"Spec (local preferred): `{SPEC_PATH.relative_to(REPO_ROOT).as_posix()}`.",
            f"Fallback URL: `{SPEC_URL}`.",
            "",
        ]
    )
    return "\n".join(lines)


def _generate_payloads_md() -> str:
    lines = [
        "# Create/Update payload reference (generated)",
        "",
        "Auto-generated from `RESOURCE_REGISTRY`, builder return types,",
        "and payload models.",
        _model_sync_summary(),
        "",
        "## Create payload/builders",
        "",
        "| Resource | SDK create support | Builder | Payload model | "
        "Required fields | Optional fields |",
        "|----------|--------------------|---------|---------------|-----------------|-----------------|",
    ]
    lines.extend(_model_sync_coverage_lines())
    for entry in sorted(RESOURCE_REGISTRY, key=lambda e: e.attr_name):
        create_supported = "create" in entry.supported_ops
        builder = entry.build_create_payload_fn
        builder_name = (
            entry.build_create_payload_fn.__name__
            if entry.build_create_payload_fn is not None
            else "N/A"
        )
        payload_model_name, payload_model = _resolve_payload_model_from_builder(builder)
        required_fields, optional_fields = _payload_field_summary(payload_model)
        if payload_model_name == "unknown" and builder is not None:
            # Keep some signal for dynamic builders when no explicit payload type.
            builder_summary = _sig_summary(builder)
            required_fields = (
                "dynamic kwargs" if "kwargs" in builder_summary else required_fields
            )
            optional_fields = (
                "see builder signature"
                if builder_summary != "none"
                else optional_fields
            )
        lines.append(
            "| "
            f"{entry.attr_name} | "
            f"{_bool_cell(create_supported)} | "
            f"{builder_name} | "
            f"{payload_model_name} | "
            f"{required_fields} | "
            f"{optional_fields} |"
        )

    lines.extend(
        [
            "",
            "## Update mutable fields",
            "",
            "| Resource | SDK update support | Mutable field paths "
            "(`get_mutable_fields_cls`) |",
            "|----------|--------------------|----------------------------------------------|",
        ]
    )
    for entry in sorted(RESOURCE_REGISTRY, key=lambda e: e.attr_name):
        update_supported = "update" in entry.supported_ops
        mutable_fields: list[str] = []
        getter = getattr(entry.model_class, "get_mutable_fields_cls", None)
        if callable(getter):
            try:
                mutable_fields = list(getter())
            except Exception:
                mutable_fields = []
        lines.append(
            "| "
            f"{entry.attr_name} | "
            f"{_bool_cell(update_supported)} | "
            f"{', '.join(mutable_fields) if mutable_fields else '—'} |"
        )

    lines.extend(
        [
            "",
            "## Identity kwargs (`list()` helpers)",
            "",
            "| Resource | Identity kwargs -> filter paths |",
            "|----------|---------------------------------|",
        ]
    )
    for entry in sorted(RESOURCE_REGISTRY, key=lambda e: e.attr_name):
        mapping = ", ".join(
            f"{k}->{v}" for k, v in sorted(entry.filter_kwarg_map.items())
        )
        lines.append(f"| {entry.attr_name} | {mapping if mapping else '—'} |")

    lines.append("")
    return "\n".join(lines)


def _format_signature_line(name: str, fn: Any) -> str:
    sig = inspect.signature(fn)
    return f"- `{name}{sig}`"


def _generate_api_surfaces_md() -> str:
    lines = [
        "# API Surfaces (generated)",
        "",
        "Auto-generated inventories for stable/public surfaces.",
        "",
        "## Top-level exports (`endorlabs.__all__`)",
        "",
    ]
    lines.extend(_model_sync_coverage_lines())
    lines.extend([f"- `{symbol}`" for symbol in sorted(endorlabs.__all__)])

    lines.extend(
        [
            "",
            "## Resource modules (`endorlabs.resources.__all__`)",
            "",
        ]
    )
    lines.extend([f"- `{symbol}`" for symbol in sorted(resource_modules.__all__)])

    lines.extend(
        [
            "",
            "## Facade method signatures",
            "",
            "### Compact facade view",
            "",
            "| Method | Primary purpose | Key parameters |",
            "|--------|------------------|----------------|",
            "| `list` | List resources with paging/filtering; non-empty `mask` → "
            "`dict` rows | `traverse`, "
            "`namespace`, `list_params`, `filter`, `mask`, `max_pages` |",
            "| `list_iter` | Stream list results; non-empty `mask` → dict items | same "
            "as `list`, iterator output |",
            "| `get` | Fetch one resource by id or resource object | "
            "`id_or_resource`, `namespace` |",
            "| `create` | Create resource from payload or builder kwargs | "
            "`payload`, `name`, `description`, `namespace_uuid`, `namespace`, "
            "`**kwargs` |",
            "| `update` | Patch resource with `update_mask` or field kwargs | "
            "`id_or_resource`, `payload`, `update_mask`, "
            "`meta_description`, `meta_tags` |",
            "| `delete` | Delete resource by id or object | "
            "`name_or_resource`, `namespace`, `ignore_missing` |",
            "| `tag` / `untag` | Tag management on resources supporting tags | "
            "`id_or_resource`, `tags`/`keys`, `namespace` |",
            "",
            "### `_ListableFacade` methods",
            "",
        ]
    )
    lines.extend(
        [
            _format_signature_line(method_name, getattr(_ListableFacade, method_name))
            for method_name in ("list", "list_iter")
        ]
    )

    lines.extend(
        ["", "### `ResourceRuntimeFacade` methods (`ResourceFacade` alias)", ""]
    )
    lines.extend(
        [
            _format_signature_line(
                method_name, getattr(ResourceRuntimeFacade, method_name)
            )
            for method_name in ("get", "create", "update", "delete", "tag", "untag")
        ]
    )

    lines.extend(
        [
            "",
            "## Client resources (registry-driven)",
            "",
            "| Attr | Resource path | Scope | Parent kind | Supported ops |",
            "|------|---------------|-------|-------------|---------------|",
        ]
    )
    for entry in sorted(RESOURCE_REGISTRY, key=lambda e: e.attr_name):
        ops = ", ".join(op for op in SDK_OP_ORDER if op in entry.supported_ops)
        lines.append(
            "| "
            f"{entry.attr_name} | "
            f"{entry.resource_name} | "
            f"{entry.scope or 'tenant'} | "
            f"{entry.parent_kind or '—'} | "
            f"{ops} |"
        )

    lines.append("")
    return "\n".join(lines)


def _write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _generate_coverage_json(spec: dict[str, Any]) -> dict[str, Any]:
    """Generate machine-readable coverage metadata for generated reference docs."""
    contract = _load_runtime_registry_contract()
    resource_rows: list[dict[str, Any]] = []
    for entry in sorted(RESOURCE_REGISTRY, key=lambda e: e.attr_name):
        spec_support = _spec_support_by_op(spec, entry.resource_name)
        sdk_support = {
            operation: operation in entry.supported_ops for operation in SDK_OP_ORDER
        }
        resource_rows.append(
            {
                "attr_name": entry.attr_name,
                "resource_name": entry.resource_name,
                "scope": entry.scope or "tenant",
                "parent_kind": entry.parent_kind,
                "supported_ops_sdk": sdk_support,
                "supported_ops_spec": spec_support,
            }
        )

    contract_path = REGISTRY_CONTRACT_PATH.relative_to(REPO_ROOT).as_posix()
    resources = contract.get("resources")
    contract_resource_count = (
        len(resources)
        if isinstance(resources, list)
        else contract.get("resource_count", 0)
    )
    return {
        "registry_contract_path": contract_path,
        "facade_contract_resource_count": contract_resource_count,
        "canonical_entity_count": _canonical_entity_count(contract),
        "resource_count": len(RESOURCE_REGISTRY),
        "resources": resource_rows,
    }


def main(argv: list[str] | None = None) -> int:
    """Generate reference docs and optionally fail when generated files drift."""
    parser = argparse.ArgumentParser(description="Generate reference docs")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if generated content differs",
    )
    args = parser.parse_args(argv)

    spec = _load_spec()
    outputs = {
        RESOURCES_DOC: _generate_resources_md(spec),
        PAYLOADS_DOC: _generate_payloads_md(),
        SURFACES_DOC: _generate_api_surfaces_md(),
        COVERAGE_JSON: (
            json.dumps(_generate_coverage_json(spec), indent=2, sort_keys=True) + "\n"
        ),
    }

    changed_files: list[Path] = []
    for path, content in outputs.items():
        changed = _write_if_changed(path, content)
        if changed:
            changed_files.append(path)

    if args.check and changed_files:
        logger.error("Generated docs are out of date:")
        for path in changed_files:
            logger.error(" - %s", path.relative_to(REPO_ROOT))
        return 1

    devtools_dir = REPO_ROOT / "devtools"
    if str(devtools_dir) not in sys.path:
        sys.path.insert(0, str(devtools_dir))
    from generate_resource_reference_pages import (
        generate_resource_reference_pages,
    )

    resource_changed = generate_resource_reference_pages()
    changed_files.extend(resource_changed)

    if changed_files:
        logger.info("Updated generated docs:")
        for path in changed_files:
            logger.info(" - %s", path.relative_to(REPO_ROOT).as_posix())
    else:
        logger.info("Generated docs are already up to date.")

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
