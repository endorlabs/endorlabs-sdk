# API Surfaces

This document defines the three supported API surfaces for the Endor Labs SDK. Every symbol in each surface **must** have full type annotations (parameters, returns, attributes) and docstrings. No assumptions; explicit contracts only.

See [resources.md](resources.md) for per-resource operations and [namespace.md](namespace.md) for namespace scoping.

---

## 1. Developer surface (primary SDK users)

**Contract:** Everything reachable via `import endorlabs` and `from endorlabs import X` — i.e. the names in [src/endorlabs/__init__.py](../../src/endorlabs/__init__.py) `__all__` — plus attributes and methods on those objects.

**Types:** Full (all parameters and return types annotated).  
**Docstrings:** Required (module, class, method/function).

### Top-level exports (`endorlabs.__all__`)

| Symbol | Kind | Types | Docstrings |
|--------|------|--------|------------|
| `APIClient` | Class | Full | Yes |
| `Client` | Class | Full | Yes |
| `AmbiguousError` | Exception | Full | Yes |
| `ConflictError` | Exception | Full | Yes |
| `EndorAPIError` | Exception | Full | Yes |
| `NotFoundError` | Exception | Full | Yes |
| `PermissionDeniedError` | Exception | Full | Yes |
| `RateLimitError` | Exception | Full | Yes |
| `ServerError` | Exception | Full | Yes |
| `UnauthorizedError` | Exception | Full | Yes |
| `ValidationError` | Exception | Full | Yes |
| `map_status_code_to_exception` | Function | Full | Yes |
| `dependency_metadata` | Module | N/A | Module docstring |
| `finding` | Module | N/A | Module docstring |
| `installation` | Module | N/A | Module docstring |
| `linter_result` | Module | N/A | Module docstring |
| `metric` | Module | N/A | Module docstring |
| `namespace` | Module | N/A | Module docstring |
| `package_version` | Module | N/A | Module docstring |
| `policy` | Module | N/A | Module docstring |
| `project` | Module | N/A | Module docstring |
| `repository` | Module | N/A | Module docstring |
| `repository_version` | Module | N/A | Module docstring |

Note: `__version__` is public but not in `__all__`; consider adding it if part of the stable SDK surface.

### Client

| Member | Types | Docstrings |
|--------|--------|------------|
| `Client.__init__(api_client=..., tenant=..., *, timeout=60.0, content_type="application/jsoncompact", accept_encoding="gzip, br, zstd", max_retries=..., base_url=..., **client_kwargs)` | Full param/return | Yes |
| `Client.whoami()` | Full; return `str \| None` | Yes |
| `Client.wait_until(predicate, timeout=60, poll_interval_max=10)` | Full; return `bool` | Yes |
| `Client.<attr>` (e.g. `.project`, `.namespace`, `.finding`) | Typed via stub (see Phase 4) | N/A (facade class docstring) |

### ResourceFacade (per resource)

Attached as `client.<attr_name>` (e.g. `client.project`). Methods:

| Method | Types | Docstrings |
|--------|--------|------------|
| `list(traverse=..., namespace=..., list_params=..., max_pages=..., **kwargs)` | Full; return `list[T]` | Yes |
| `lookup(...)` | Full; return `T` | Yes |
| `list_iter(...)` | Full; return `Iterator[T]` | Yes |
| `get(id_or_resource: str \| T, namespace=...)` | Full; overloads for str vs T (preferred) | Yes |
| `create(payload, namespace=...)` | Full | Yes |
| `update(id_or_resource, payload=..., *, update_mask, namespace=...)` | Full; overloads (preferred) | Yes |
| `delete(name_or_resource, namespace=..., *, ignore_missing=...)` | Full; overloads (preferred) | Yes |
| `tag(id_or_resource, tags, namespace=...)` | Full | Yes |
| `untag(id_or_resource, keys, namespace=...)` | Full | Yes |

### ScanLogsFacade

| Member | Types | Docstrings |
|--------|--------|------------|
| `get_logs(scan_result_uuid, namespace=..., max_entries=..., log_levels=..., start_time=..., end_time=..., newest_first=...)` | Full | Yes |

### Exceptions (in `__all__`)

All exception classes and `map_status_code_to_exception` must have full types and docstrings (see [src/endorlabs/exceptions.py](../../src/endorlabs/exceptions.py)).

### Resource modules (in `__all__`)

For each of `dependency_metadata`, `finding`, `installation`, `linter_result`, `metric`, `namespace`, `package_version`, `policy`, `project`, `repository`, `repository_version`: Pydantic models, payload/response types, and resource-specific convenience functions are accessible via `endorlabs.resources.<name>`. CRUD operations are performed exclusively through the `Client` facade (`client.<resource>.list()`, `.get()`, etc.).

---

## 2. Module-level surface (advanced usage)

**Contract:** Explicit imports such as `from endorlabs.operations import ...`, `from endorlabs.utils import ...`, `from endorlabs.types import ...`, `from endorlabs.resources import <module>`, and direct use of `APIClient`.

**Types:** Full.  
**Docstrings:** Yes (class/function/module).

### APIClient

**Location:** [src/endorlabs/api_client.py](../../src/endorlabs/api_client.py)

| Surface | Types | Docstrings |
|---------|--------|------------|
| `APIClient` class | Full | Yes |
| All public methods and attributes | Full | Yes |

### endorlabs.types

**Location:** [src/endorlabs/types.py](../../src/endorlabs/types.py)

All public types: `ListParameters`, `ErrorResponse`, `ResourceMeta`, `TenantMeta`, `APIResponse`, `ValidationResult`, `SchemaDriftInfo`, and Literal aliases (`ResourceType`, `OperationType`, `StatusType`, `SeverityType`, `PlatformType`, `EcosystemType`, `FindingCategoryType`, `PolicyType`), plus `ResourceDict`, `ResourceList`, `NamespaceStr`, `UUIDStr`, `TagList`, `UpdateMask`, `ResourceOperation`. Each must have full types and docstrings (class or alias description).

### endorlabs.resources (each module in `resources/__all__`)

**Location:** [src/endorlabs/resources/](../../src/endorlabs/resources/)

Modules: `api_key`, `audit_log`, `authorization_policy`, `dependency_metadata`, `finding`, `finding_log`, `installation`, `linter_result`, `metric`, `namespace`, `package_license`, `package_version`, `policy`, `project`, `repository`, `repository_version`, `scan_log_request`, `scan_profile`, `scan_result`, `semgrep_rule`.

For each module, public surface: Pydantic models (payload/response types) and resource-specific convenience functions (e.g. `associate_scan_profile_with_project`). CRUD operations (`list`, `get`, `create`, `update`, `delete`) are handled by `BaseResourceOperations` via the `Client` facade — not as module-level functions. Full types and docstrings required.

### endorlabs.operations

**Location:** [src/endorlabs/operations/__init__.py](../../src/endorlabs/operations/__init__.py)

**Symbols in `__all__`:** `BaseResourceOperations` — generic CRUD engine that powers the `Client` facade. Accepts resource name, model class, and an `APIClient` instance. Provides `list()`, `get()`, `create()`, `update()`, `delete()` methods. Full types and docstrings required.

### endorlabs.utils

**Location:** [src/endorlabs/utils/__init__.py](../../src/endorlabs/utils/__init__.py)

**Symbols in `__all__`:** `SchemaDriftDetector`, `compute_attribute_overlap_report`, `compute_model_consistency_diff`, `enumerate_sdk_models_flat_paths`, `enumerate_spec_fields_flat`, `enumerate_spec_top_level_refs`, `load_spec`, `resolve_namespace_for_resource`, `run_model_consistency_report`. Full types and docstrings required.

### endorlabs.models

**Location:** [src/endorlabs/models/__init__.py](../../src/endorlabs/models/__init__.py)

**Symbols in `__all__`:** `BaseMeta`, `BaseResource`, `BaseSpec`, `Context`, `IngestedObject`, `ProcessingStatus`, `TenantMeta`. Full types and docstrings required.

---

## 3. Raw client surface

**Contract:** Use of `APIClient` only (no `Client`, no facades). Same as module-level but scoped to [src/endorlabs/api_client.py](../../src/endorlabs/api_client.py): every public method and attribute must have full types and docstrings.

**Deliverable:** Covered by the Module-level section above; raw client = `APIClient` only.

---

## Summary

| Surface | Entry point | Types | Docstrings |
|---------|-------------|--------|------------|
| Developer | `import endorlabs`, `endorlabs.__all__`, `Client`, facades | Full | Required |
| Module-level | `endorlabs.api_client`, `endorlabs.types`, `endorlabs.resources.*`, `endorlabs.operations`, `endorlabs.utils`, `endorlabs.models` | Full | Required |
| Raw client | `APIClient` only | Full | Required |

Internal symbols (not in the above) use a leading `_` and are documented as internal; they are not part of the supported API contract.
