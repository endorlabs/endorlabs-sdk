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

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import endorlabs  # noqa: E402
from endorlabs import resources as resource_modules  # noqa: E402
from endorlabs.facade import ResourceRuntimeFacade, _ListableFacade  # noqa: E402
from endorlabs.registry import RESOURCE_REGISTRY  # noqa: E402

logger = logging.getLogger(__name__)

SPEC_PATH = REPO_ROOT / ".endorlabs-context" / "openapiv2.swagger.json"
SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"
MODEL_SYNC_MAPPING_PATH = (
    REPO_ROOT
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "mapping"
    / "entity_mapping.json"
)
MODEL_SYNC_MANIFEST_PATH = (
    REPO_ROOT
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "artifacts_manifest.json"
)
FACADE_CONTRACT_PATH = (
    REPO_ROOT / "workspace" / "model-sync" / "custom_mapping" / "facade_contract.json"
)
REGISTRY_PARITY_REPORT_PATH = (
    REPO_ROOT
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "mapping"
    / "registry_parity_report.json"
)
OPERATION_PATH_METADATA_PATH = (
    REPO_ROOT
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "mapping"
    / "operation_path_metadata.json"
)
PAYLOAD_SCHEMAS_PATH = (
    REPO_ROOT
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "mapping"
    / "payload_schemas.json"
)
RUNTIME_INDEX_PATH = (
    REPO_ROOT
    / "workspace"
    / "model-sync"
    / "custom_mapping"
    / "mapping"
    / "runtime_index.json"
)

GENERATED_REFERENCE_DIR = REPO_ROOT / "docs" / "generated-reference"
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


def _model_sync_summary() -> str:
    """Return canonical model-sync summary for doc propagation."""
    if not MODEL_SYNC_MAPPING_PATH.exists():
        return "Model sync mapping: unavailable."
    try:
        payload = json.loads(MODEL_SYNC_MAPPING_PATH.read_text(encoding="utf-8"))
        entries = payload.get("entries")
        count = len(entries) if isinstance(entries, list) else 0
        mapping_path = MODEL_SYNC_MAPPING_PATH.relative_to(REPO_ROOT).as_posix()
        return f"Model sync mapping: `{mapping_path}` ({count} entities)."
    except Exception:
        return "Model sync mapping: unreadable."


def _model_sync_coverage_lines() -> list[str]:
    """Return model-sync coverage lines sourced from manifests."""
    entry_count = "unavailable"
    file_count = "unavailable"
    contract_resources = "unavailable"
    parity_status = "unavailable"
    operation_count = "unavailable"
    payload_resource_count = "unavailable"
    runtime_index_models = "unavailable"

    if MODEL_SYNC_MAPPING_PATH.exists():
        try:
            payload = json.loads(MODEL_SYNC_MAPPING_PATH.read_text(encoding="utf-8"))
            entry_count = str(payload.get("entry_count", "unavailable"))
        except Exception:
            entry_count = "unreadable"
    if MODEL_SYNC_MANIFEST_PATH.exists():
        try:
            payload = json.loads(MODEL_SYNC_MANIFEST_PATH.read_text(encoding="utf-8"))
            file_count = str(payload.get("file_count", "unavailable"))
        except Exception:
            file_count = "unreadable"
    if FACADE_CONTRACT_PATH.exists():
        try:
            payload = json.loads(FACADE_CONTRACT_PATH.read_text(encoding="utf-8"))
            contract_resources = str(payload.get("resource_count", "unavailable"))
        except Exception:
            contract_resources = "unreadable"
    if REGISTRY_PARITY_REPORT_PATH.exists():
        try:
            payload = json.loads(
                REGISTRY_PARITY_REPORT_PATH.read_text(encoding="utf-8")
            )
            parity_status = str(payload.get("status", "unavailable"))
        except Exception:
            parity_status = "unreadable"
    if OPERATION_PATH_METADATA_PATH.exists():
        try:
            payload = json.loads(
                OPERATION_PATH_METADATA_PATH.read_text(encoding="utf-8")
            )
            operation_count = str(payload.get("operation_count", "unavailable"))
        except Exception:
            operation_count = "unreadable"
    if PAYLOAD_SCHEMAS_PATH.exists():
        try:
            payload = json.loads(PAYLOAD_SCHEMAS_PATH.read_text(encoding="utf-8"))
            payload_resource_count = str(payload.get("resource_count", "unavailable"))
        except Exception:
            payload_resource_count = "unreadable"
    if RUNTIME_INDEX_PATH.exists():
        try:
            payload = json.loads(RUNTIME_INDEX_PATH.read_text(encoding="utf-8"))
            model_index = payload.get("model_class_import_by_name")
            runtime_index_models = (
                str(len(model_index))
                if isinstance(model_index, dict)
                else "unavailable"
            )
        except Exception:
            runtime_index_models = "unreadable"

    return [
        "## Model-sync coverage snapshot",
        "",
        f"- mapped entities: `{entry_count}`",
        f"- generated artifact files: `{file_count}`",
        f"- facade contract resources: `{contract_resources}`",
        f"- registry parity status: `{parity_status}`",
        f"- operation metadata entries: `{operation_count}`",
        f"- payload schema resources: `{payload_resource_count}`",
        f"- runtime model import index entries: `{runtime_index_models}`",
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
            "Spec (local preferred): `.endorlabs-context/openapiv2.swagger.json`.",
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
            "## Identity kwargs (`list()` / `lookup()` helpers)",
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
            "| `list` | List resources with paging/filtering | `traverse`, "
            "`namespace`, `list_params`, `filter`, `mask`, `max_pages` |",
            "| `lookup` | Return exactly one matching resource | `filter`, "
            "identity kwargs via `filter_kwarg_map`, `max_pages` |",
            "| `list_iter` | Streaming iteration over list results | same "
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
            for method_name in ("list", "lookup", "list_iter")
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
    mapping_payload: dict[str, Any] = {}
    manifest_payload: dict[str, Any] = {}
    facade_contract_payload: dict[str, Any] = {}
    registry_parity_payload: dict[str, Any] = {}
    operation_path_metadata_payload: dict[str, Any] = {}
    payload_schemas_payload: dict[str, Any] = {}
    runtime_index_payload: dict[str, Any] = {}
    if MODEL_SYNC_MAPPING_PATH.exists():
        try:
            mapping_payload = json.loads(
                MODEL_SYNC_MAPPING_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            mapping_payload = {}
    if MODEL_SYNC_MANIFEST_PATH.exists():
        try:
            manifest_payload = json.loads(
                MODEL_SYNC_MANIFEST_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            manifest_payload = {}
    if FACADE_CONTRACT_PATH.exists():
        try:
            facade_contract_payload = json.loads(
                FACADE_CONTRACT_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            facade_contract_payload = {}
    if REGISTRY_PARITY_REPORT_PATH.exists():
        try:
            registry_parity_payload = json.loads(
                REGISTRY_PARITY_REPORT_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            registry_parity_payload = {}
    if OPERATION_PATH_METADATA_PATH.exists():
        try:
            operation_path_metadata_payload = json.loads(
                OPERATION_PATH_METADATA_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            operation_path_metadata_payload = {}
    if PAYLOAD_SCHEMAS_PATH.exists():
        try:
            payload_schemas_payload = json.loads(
                PAYLOAD_SCHEMAS_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            payload_schemas_payload = {}
    if RUNTIME_INDEX_PATH.exists():
        try:
            runtime_index_payload = json.loads(
                RUNTIME_INDEX_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            runtime_index_payload = {}

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

    mapping_path = MODEL_SYNC_MAPPING_PATH.relative_to(REPO_ROOT).as_posix()
    manifest_path = MODEL_SYNC_MANIFEST_PATH.relative_to(REPO_ROOT).as_posix()
    contract_path = FACADE_CONTRACT_PATH.relative_to(REPO_ROOT).as_posix()
    parity_path = REGISTRY_PARITY_REPORT_PATH.relative_to(REPO_ROOT).as_posix()
    operation_path = OPERATION_PATH_METADATA_PATH.relative_to(REPO_ROOT).as_posix()
    payload_path = PAYLOAD_SCHEMAS_PATH.relative_to(REPO_ROOT).as_posix()
    runtime_index_path = RUNTIME_INDEX_PATH.relative_to(REPO_ROOT).as_posix()
    return {
        "model_sync_mapping_path": mapping_path,
        "model_sync_entry_count": mapping_payload.get("entry_count", 0),
        "model_sync_manifest_path": manifest_path,
        "model_sync_manifest_file_count": manifest_payload.get("file_count", 0),
        "facade_contract_path": contract_path,
        "facade_contract_resource_count": facade_contract_payload.get(
            "resource_count", 0
        ),
        "registry_parity_report_path": parity_path,
        "registry_parity_status": registry_parity_payload.get("status"),
        "registry_parity_missing_in_mapping_count": len(
            registry_parity_payload.get("missing_in_mapping", [])
            if isinstance(registry_parity_payload.get("missing_in_mapping"), list)
            else []
        ),
        "operation_path_metadata_path": operation_path,
        "operation_path_metadata_count": operation_path_metadata_payload.get(
            "operation_count", 0
        ),
        "payload_schemas_path": payload_path,
        "payload_schema_resource_count": payload_schemas_payload.get(
            "resource_count", 0
        ),
        "runtime_index_path": runtime_index_path,
        "runtime_model_import_count": len(
            runtime_index_payload.get("model_class_import_by_name", {})
            if isinstance(runtime_index_payload.get("model_class_import_by_name"), dict)
            else {}
        ),
        "runtime_capability_resource_count": len(
            runtime_index_payload.get("capability_by_resource", {})
            if isinstance(runtime_index_payload.get("capability_by_resource"), dict)
            else {}
        ),
        "resource_count": len(RESOURCE_REGISTRY),
        "resources": resource_rows,
    }


def main() -> int:
    """Generate reference docs and optionally fail when generated files drift."""
    parser = argparse.ArgumentParser(description="Generate reference docs")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if generated content differs",
    )
    args = parser.parse_args()

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
