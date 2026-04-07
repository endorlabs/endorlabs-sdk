# Resource Implementation Rules of Engagement

Checklists for implementing new Endor Labs resources. CRUD operations are handled by `BaseResourceOperations` via the `Client` facade; resource modules contain Pydantic models and convenience functions only. See [contracts.md](../contracts.md) for naming, spec path, list params, and update behavior. Implement per `.cursor/rules/resource-patterns.mdc`.

## Canonical Generation Policy

- Canonical model generation path is custom mapping from `.endorlabs-context/openapiv2.swagger.json` to deterministic Pydantic modules.
- Resource eligibility defaults to include when `x-internal != true`.
- Explicit include exceptions are allowed for existing modeled SDK resources (registry-backed allowlist) where upstream metadata is incomplete/inconsistent.
- Deterministic mapping is mandatory: stable bucketing, stable naming transforms, and stable `entity -> module` mapping manifest.

## Phase 0: API Analysis (MANDATORY)

- [ ] Review OpenAPI spec for the resource (local: `.endorlabs-context/openapiv2.swagger.json`; see [contracts.md](../contracts.md)).
- [ ] Note service name, URL endpoints, HTTP methods.
- [ ] Validate generation eligibility (`x-internal` + explicit modeled-resource exception allowlist).
- [ ] Use live API responses as canonical structure; run endorctl list/get as needed.
- [ ] Confirm BaseResource compatibility; list_params (filter, mask, page_size, traverse) and update_mask support.

## Phase 1: Implementation

- [ ] Models: Meta, Spec, Resource extending BaseResource; schema drift detection per base.
- [ ] Confirm model sync parity with canonical generated bucket for this resource domain before adding manual model deltas.
- [ ] **Field aliasing:** Reserved/invalid API key -> alias (Tier 1). Otherwise 1:1 with spec (Tier 2). **Greenfield:** Prefer Python name = spec key for shared fields (`context`, `processing_status`, `index_data`). If you use a prefixed name with alias for a shared concept, register in [model_consistency.SDK_FIELD_ALIAS_TO_SHARED](../../.github/scripts/model_consistency.py) (Tier 3). See [contracts.md](../contracts.md) (Models and API parity -> Field aliasing).
- [ ] CRUD: Handled by `BaseResourceOperations` via the facade — no module-level CRUD wrappers needed. The facade delegates `list`, `get`, `create`, `update`, `delete` to `BaseResourceOperations` using registry metadata.
- [ ] Update: `update_mask` is a comma-separated string at the facade level, converted to a list internally. For UUID+payload updates, `update_mask` is required. Resource-instance field-kwargs updates may auto-derive the mask.
- [ ] Errors: use exception classes exported by `endorlabs` (implemented in `endorlabs.core.exceptions`); log full response text; no truncation.
- [ ] **Create/update fields:** The allowed create fields are defined in the resource’s `build_create_payload`; the allowed update fields are defined by the model’s `get_mutable_fields_cls()` and `get_immutable_fields_cls()` (see BaseResource). When adding a resource, override these classmethods on the model if the resource has more than the base default. The facade may expose a subset as explicit optional kwargs.
- [ ] Docstrings: Args, Returns, Raises so Pydantic/Pyright and IDE are self-explanatory; if a resource module lacks these, treat as a gap and add them.

## Phase 2: Expose on Client (optional)

If the resource should be available via the resource-oriented Client (e.g. `client.Project.list()`):

- [ ] Ensure model-sync emits the resource row in `src/endorlabs/generated/registry_contract.py` (from canonical artifacts).
- [ ] If the SDK needs intentional divergence, add a minimal override in `src/endorlabs/registry_overlay.py` (allowed keys only).
- [ ] Do not hand-wire the resource in `Client.__init__`; facades are attached from the effective contract. Tags paths for .tag()/.untag() are derived from the model’s mutable fields (no separate map).

No full code templates here; follow existing resource modules and [resource-patterns.mdc](../../.cursor/rules/resource-patterns.mdc).

## Phase 2b: Tests (canonical order)

Each resource test file follows the same order where the registry supports the operation:

1. **LIST** — From tenant root (`root_namespace`) with `traverse=True`, limited pages. Assert result is a list.
2. **GET** — If LIST returned items, GET the first item (pass resource object so namespace is derived; avoids 404 after traverse). If LIST was empty, skip with "No resources in scope (empty; may be filter/auth/scope)".
3. **Create** — For resources with `create_fn`: create one, capture UUID for teardown.
4. **Update** — For resources with `update_fn` not None: update the resource created in (3).
5. **Delete** — For resources with `delete_fn`: delete the resource created in (3) for cleanup.

**Fixtures:** Use conftest `api_client`, `namespace`, `root_namespace`. For resources where `"update" not in entry.supported_ops` (api_keys, audit_logs, finding_logs, linter_results), add a test that asserts `client.<attr>.update(...)` raises `NotImplementedError`.

**Checklist after changes:** Every registry entry has a test file; List/Get Y for all; Update N tests for api_keys, audit_logs, finding_logs, linter_results; `pytest tests/test_openapi_spec.py -v` passes when spec is present.
