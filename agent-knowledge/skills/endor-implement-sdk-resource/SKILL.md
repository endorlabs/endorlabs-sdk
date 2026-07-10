---
name: endor-implement-sdk-resource
description: |
  Use when extending the SDK client surface after OpenAPI changes—model sync,
  registry overlay, payload builders, and integration tests—when a new API resource
  appears, facade behavior diverges from the generated contract, or list/get/create
  needs validation. Not for hand-implementing every resource from scratch.
---

# Extend the SDK client surface (model-sync-first)

The SDK **generates** registry rows, models, and facades from OpenAPI. Contributor work is regen, minimal overlay, hand deltas in `resources/` when needed, and integration tests.

## Phase 0: API analysis (mandatory)

Follow [api-validation.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/api-validation.md) (OpenAPI grep, optional endorctl in namespace scope, operations matrix from generated reference).

## Phase 1: Regenerate and review contract

```bash
uv run python devtools/codegen/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
```

- [ ] Resource row in `src/endorlabs/generated/registry_contract.py`
- [ ] Generated model shard under `src/endorlabs/generated/models/` (or hand module if exempt)
- [ ] `client_surface.pyi` regen has no unexpected drift
- [ ] If behavior differs from API: minimal change in `src/endorlabs/registry_overlay.py` (allowed keys only) or `devtools/codegen/model_sync_profiles/`

**Hand-written `src/endorlabs/resources/{name}.py` only when needed:**

- Extend `resources.base.BaseResource` / `BaseSpec` for `Client` return types
- Policy nested specs: `finding_config.py`, `notification_config.py`, `exception_config.py` as siblings (product policy UI tabs)
- `build_create_payload` / create convenience; `extra="allow"` on specs for forward compat
- Field aliasing per [contracts.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contracts.md); Tier 3 aliases in `resources/field_aliases.py`
- Resource-specific helpers (not module-level CRUD — facade uses `BaseResourceOperations`)
- Do **not** add per-resource `detect_schema_drift` validators — use model-sync parity ([endor-model-sync-drift](../endor-model-sync-drift/SKILL.md))

Do **not** hand-wire facades in `Client.__init__`.

Architecture: [architecture.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/architecture.md) (consumer vs generated models).

## Phase 2: Facade and consumer UX

- [ ] List/get/create kwargs match registry and [contracts.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contracts.md)
- [ ] `update_mask` required for sparse PATCH where applicable
- [ ] Scope (`tenant`, `oss`, `system`) correct in overlay if not tenant-default
- [ ] Docstrings on public helpers in `resources/` (Args, Returns, Raises)

Custom workflow facades (e.g. `CallGraphData`) are rare append-only entries in `registry.py` — prefer overlay + generated contract.

## Phase 3: Integration tests

Follow [integration-resource-tests.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/integration-resource-tests.md):

1. LIST in `namespace` (no traverse) — generic: `TEST_PAGE_SIZE` / `TEST_MAX_PAGES`; logs: `log_list_kwargs()`
2. GET first row (resource object for namespace)
3. Create / update / delete where supported, with teardown
4. `NotImplementedError` for update on read-only kinds

Traverse coverage: `tests/integration/client/test_concurrent_list.py`. List performance: [list-query-performance.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/list-query-performance.md).

## Checklist

- [ ] Phase 0: API analysis (spec ± live)
- [ ] Model sync regen committed; provenance current
- [ ] Overlay / `resources/` deltas minimal and justified
- [ ] Integration test file under `tests/integration/resources/`
- [ ] `uv run ruff check .` and `uv run pyright` pass
- [ ] `uv run pytest tests/unit -m "not interactive and not long"` pass
- [ ] Integration tests pass locally with `ENDOR_*` creds when applicable
- [ ] New or changed env vars cite Endor Labs docs; README/contracts updated; read-only `os.getenv` (no `os.environ` mutation) — rule `endor-environment-variables`
