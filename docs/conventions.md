# SDK Conventions

Single source of truth for Endor Cockpit SDK usage. Link here from other docs instead of re-stating. For SDK implementation, **practices** means the patterns in this document and in [rules-of-engagement](rules-of-engagement/) (resource-implementation, architecture).

## Canonical naming

- Use `tenant.namespace.child` only; never UUIDs in namespace paths.
- Example: `tenant_meta_namespace="endor-solutions-tgowan"` or `"tenant.bu.team"`.

## OpenAPI / spec

- The spec is not in the repo; use <https://api.endorlabs.com/download/openapiv2.swagger.json>. The schema drift workflow downloads it to `external_docs/openapi-swagger.json` (gitignored) in CI. For a single local step that creates `external_docs/` with both spec and user docs (for full IDE context), see [CONTRIBUTORS.md](../CONTRIBUTORS.md) and [scripts/README.md](../scripts/README.md).
- List endpoints: `v1/namespaces/{tenant_meta.namespace}/{resource_name}` (e.g. `findings`, `projects`).
- Update (PATCH): Collection URL; UUID and payload in request body; optional `request.update_mask`.

## Models and API parity

- **Reserved words:** Use a Python-safe name (e.g. `from_`) and `Field(alias="from")`; never use reserved words as field names.
- **Python names in code:** Use Python field names in code; API/spec names only via `Field(alias=...)`. Tooling (e.g. model consistency) uses Python names.
- **Nested models:** Use typed Pydantic models for nested maps/arrays; "extra in SDK" for those paths in consistency reports is expected; do not remove typing to match spec flattening.
- **Shared fields (greenfield):** Prefer Python name = spec key for shared concepts (`context`, `processing_status`, `index_data`). Use the same attribute name in all resources; no prefixed names and no registration in `model_consistency.SDK_FIELD_ALIAS_TO_SHARED` for these.
- **Option/config names:** SDK may use clearer names than spec (e.g. `assume_numbers_are_safe`); use `Field(alias=...)` when the API expects the spec key.
- **Consistency check:** Model consistency uses Python field names; the spec enumerator follows `properties` and top-level `$ref` only (not `additionalProperties`/`items`). Nested SDK paths therefore appear as "extra" by design.
- **Spec-driven UX:** Expose spec-defined attributes and types with sources of truth in resource modules and models; see [rules-of-engagement](rules-of-engagement/) (resource-implementation, architecture).

**Field aliasing:**

- **Tier 1 (mandatory):** Alias only when the API key is a reserved word or invalid in Python (e.g. `from` → `from_`). Style: trailing underscore.
- **Tier 2 (case):** API is snake_case per spec; do not add a global camelCase→snake_case generator unless the API/spec uses camelCase. Prefer 1:1 Python names with API keys.
- **Tier 3 (semantic renames):** Avoid renaming for "prettiness." Alias only when the API name is misleading, excessively long, or ambiguous in context; document the reason. **Greenfield:** Use Python name = spec key for shared fields (`context`, `processing_status`, `index_data`); no prefixed names. If you do use a prefixed Python name with `alias="..."` for a shared concept, register it in [model_consistency.SDK_FIELD_ALIAS_TO_SHARED](../src/endorlabs/utils/model_consistency.py).
- **UX:** Base models use `populate_by_name=True` so both the Python attribute and the API key can be used when constructing/validating. Request serialization uses `by_alias=True` so outgoing JSON matches the API.

**Style heuristic (aliasing):**

- **Default:** Python attribute name = API key (1:1) when the API key is a valid, non-reserved Python identifier.
- **Syntax (Tier 1):** API key is reserved (`from`, `class`, `global`) or invalid in Python (e.g. hyphen) — use safe Python name (trailing underscore or hyphen→underscore) and `Field(alias="api_key")`.
- **Case (Tier 2):** API is snake_case per spec; prefer 1:1. No global camelCase→snake_case unless the spec uses camelCase.
- **Semantic / subclass (Tier 3):** Prefer Python name = API key for shared fields (`context`, `processing_status`, `index_data`). If you use a prefixed Python name with `Field(alias="...")` for a shared concept, register it in [model_consistency.SDK_FIELD_ALIAS_TO_SHARED](../src/endorlabs/utils/model_consistency.py). Do not rename for brevity or preference when the API key is already clear and valid.
- **Config:** Base models use `populate_by_name=True` and `extra="allow"`; resource models often use `extra="ignore"`. Serialization uses `by_alias=True` so outgoing JSON matches the API.

## Traverse

- `ListParameters(traverse=True)` for tenant-wide list operations.
- Pass to the resource's `list_*` function; the client sends `list_parameters.traverse=true`.
- Use when namespace is unknown or you need all child namespaces.

## Namespace scoping (resource-scoped operations)

When you have a resource (e.g. from `list(traverse=True)`), pass the **resource object** to `get`, `update`, or `delete` so the SDK anchors the operation to the resource's namespace and avoids 404 (context mismatch). Example: `client.project.delete(target)` instead of `client.project.delete(target.uuid, namespace=target.tenant_meta.namespace)`.

- **get / update / delete:** Accept either a UUID string or a resource object. When a resource object is passed, namespace is derived from `resource.tenant_meta.namespace`.
- **List/filter scoped to a resource:** For list or filter that are "in scope of this resource" (e.g. filter by project UUID), use the resource's namespace: `resolve_namespace_for_resource(resource, client_default)` or `resource.tenant_meta.namespace`. For child resources (e.g. scan_results, repository_versions), use `list(parent=resource)` so the SDK derives namespace and `meta.parent_uuid` filter from the parent; only resources with a registry `parent_kind` support `parent=`.
- **Resource namespace:** Use `resource.namespace` (canonical namespace for the resource, or `None` when `tenant_meta` is absent) instead of `resource.tenant_meta.namespace` when you need the scope string.
- **Discovery (no resource yet):** Use tenant root + `traverse=True`.

Helper: `endorlabs.utils.resolve_namespace_for_resource(resource, fallback)` returns `resource.tenant_meta.namespace` when present, else `fallback`.

## List parameters

- **filter**: `list_params.filter` → `list_parameters.filter` (e.g. `spec.level==FINDING_LEVEL_CRITICAL`). Which **rows** match (query).
- **mask**: `list_params.mask` → `list_parameters.mask` (e.g. `meta.name,spec.level`) for response field selection. Which **fields** are returned (projection). Do not combine with filter; they are separate concepts.
- **page_size**, **page_token**, **page_id**: Pagination; only set `page_size` when you need a specific size (API default otherwise). `page_id` is an alternative pagination start (aligns with endorctl `--page-id`).
- **sort_by**, **desc**: Sorting. `sort_by` is the field path (e.g. `meta.create_time`); `desc=True` for descending, `False` or omit for ascending. The API expects `list_parameters.sort.path` and `list_parameters.sort.order` (enum: `SORT_ENTRY_ORDER_ASC`, `SORT_ENTRY_ORDER_DESC`). Legacy `sort_field` and `sort_order` are still supported and normalized to the same API params.
- **traverse**: See above.
- **count**, **from_date**, **to_date**: see `endorlabs.types.ListParameters` (Field descriptions there).
- **archive**, **pr_uuid**: Common params (fetch from archive, scope to a PR scan). Exposed as typed kwargs on the facade; also available via `list_params=ListParameters(...)`. **list_all** is not on the facade; list operations always use full pagination (list_parameters.list_all=true). Use `list_params=ListParameters(list_all=False)` only when you need to cap at one page.
- **Grouping/aggregation**: `group_aggregation_paths`, `group_by_time`, `group_by_time_interval`, `group_unique_count_paths`, etc. Use `list_params=ListParameters(...)` for full control; see `endorlabs.types.ListParameters`.
- Defined in `endorlabs.types.ListParameters`; see [src/endorlabs/types.py](../src/endorlabs/types.py).

**Consumer UX:** Common params (filter, mask, traverse, page_size, page_token, page_id, sort_by, desc, count, from_date, to_date, archive, pr_uuid) are **flat kwargs** on `client.<resource>.list()`. List operations use full pagination by default (list_all=true). Pass `list_params=ListParameters(...)` for grouping and other options. Do not combine filter and mask into one parameter. Details and spec-driven UX: [guides/consumer-ux-list-update.md](guides/consumer-ux-list-update.md).

## Create (decoupled)

- **create** accepts either **payload** (CreateXPayload) for backward compatibility or **kwargs** that are passed to the resource’s `build_create_payload` (when the resource has a builder). Use `client.<resource>.create(name="...", namespace="...")` or `client.<resource>.create(payload=CreateXPayload(...))`. Responses stay `Resource` with `.spec`; no flattened view. See [reference/create-update-payloads.md](reference/create-update-payloads.md).
- **Common facade params:** The facade may expose a small set of optional kwargs (e.g. `name`, `description`, `namespace_uuid`) merged into the builder path; the **allowed set** is defined only by the resource’s `build_create_payload`. Add an explicit facade param when the field is shared across many resources and commonly used (e.g. by endorctl).

## Update and update_mask

- **update_mask** = which **fields** to patch (PATCH body); separate from list **mask** (response projection). Do not combine with filter or list mask.
- Most resources: `update_*` **requires** `update_mask: str` (comma-separated paths). Sparse PATCH is always used; the base layer builds a sparse request body and sends `request.update_mask`. Missing or empty mask raises `ValidationError`.
- Namespace: `update_mask` is **required** (e.g. `"meta.description"`); API returns 400 without at least one field.
- Immutable fields in `update_mask` are rejected by the SDK before the request.

**Implicit update_mask (field kwargs):** When `update_mask` is omitted, the facade accepts field kwargs (e.g. `meta_description`, `meta_tags`, `scan_state`). The mask is derived from those kwargs and the payload is built by the resource (see `BaseResource.update` and `_build_update_payload`). Use either `client.<resource>.update(resource, meta_description="...", meta_tags=[...])` or `resource.update(client.<resource>, meta_description="...")`. Which fields are allowed is defined by the model’s mutable paths (e.g. `Project.get_mutable_fields()`).
- **Common facade params:** Optional facade params (e.g. `meta_description`, `meta_tags`) are merged into the field-kwargs path; the **allowed set** is defined only by the resource’s `get_mutable_fields()` / `get_update_kwarg_to_path()`.

## Type overrides and Pyright

- **Variable override (reportIncompatibleVariableOverride):** Resource and model subclasses override base class attributes with a more specific type (e.g. `spec: FindingSpec` on a subclass of `BaseResource`). Pyright flags these because the base declares a broader type. The overrides are intentional and required for API parity; minimal `# pyright: ignore[reportIncompatibleVariableOverride]` with a reference to this section is acceptable.
- **Method override (reportIncompatibleMethodOverride):** Overrides such as `model_dump` (Pydantic) or `_missing_` (Enum) that intentionally widen or match a base signature are documented here; minimal ignore with reference is acceptable.
- **Private usage (reportPrivateUsage):** Cross-module use of `_`-prefixed helpers (e.g. `operations._build_params`) is intentional internal coupling between resource and operations layers. Document and keep minimal ignore with reference to this section.

## Errors

- Use `endorlabs.exceptions`; resources may return `None` on 404 where documented.
- Log full `response.text` on errors; no truncation in error handling.
- gRPC-derived status codes are mapped to HTTP and typed exceptions where documented.

