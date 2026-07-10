# Integration resource tests

Checklist for **integration** tests that validate registry-backed facades against the live API. The SDK surface is normally **generated** by model sync; this doc does not cover hand-implementing models or registry rows. See [architecture.md](architecture.md) for contributing to the generated client surface and [api-validation.md](api-validation.md) for pre-flight OpenAPI checks.

## When to add tests

After model sync exposes a resource on `Client` (`src/endorlabs/generated/registry_contract.py`), ensure list/get coverage via the shared harness and add or extend `tests/integration/resources/test_{resource}.py` only for **resource-specific** behavior (create/update/delete, PATCH, parent scope, expected 403, log-style bounds, OSS/system namespace).

**Default list→get** for standard tenant-scoped kinds lives in
[`test_resource_list_get_roundtrip.py`](../../tests/integration/resources/test_resource_list_get_roundtrip.py).
Do not re-add per-resource `test_*_list` / `test_*_get` boilerplate when that
harness already covers the kind.

## Canonical test order

Shared list/get: the roundtrip harness. Per-resource files keep extras only,
in this order where the registry supports the operation:

1. **LIST / GET** — Prefer the roundtrip harness. If a kind needs unique list
   filters or get assertions, keep those here (still **no `traverse`** in
   per-resource CRUD; **`traverse=True`** is covered in
   [tests/integration/client/test_concurrent_list.py](../../tests/integration/client/test_concurrent_list.py)).
2. **Create** — For resources with `create` in `supported_ops`: create one, capture UUID for teardown.
3. **Update** — For resources with `update` in `supported_ops`: update the resource created in (2).
4. **Delete** — For resources with `delete` in `supported_ops`: delete the resource created in (2) for cleanup.

**Fixtures:** Use integration conftest `api_client`, `namespace`, `root_namespace`. Prefer `endor_client = endorlabs.Client(tenant=namespace, api_client=api_client)` for LIST/GET in namespace scope.

**Cleanup:** Every CREATE test must use try/finally (or teardown) so cleanup runs on pass, failure, or exception.

**No-update resources:** For resources where update is unsupported (`api_keys`, `audit_logs`, `finding_logs`, `linter_results`, …), add a test that asserts `client.<Kind>.update(...)` raises `NotImplementedError`.

## Pagination profiles

### Generic resources

Use `TEST_PAGE_SIZE` and `TEST_MAX_PAGES` from [tests/conftest.py](../../tests/conftest.py) (`page_size=1`, `max_pages=1`) for typical integration LIST calls. See [list-query-performance.md](list-query-performance.md) for scope, filters, and debugging slow lists.

### Log-style resources

`AuditLog`, `FindingLog`, `AuthenticationLog`, and ScanLog list fixtures use the **log list profile** in `tests/conftest.py`:

- **`TEST_LOG_LIST_MAX_PAGES`** — cap client page fetches (typically `1`)
- **`TEST_LOG_LIST_MAX_ROWS`** — safety cap on rows returned in one bounded list
- **Do not** force `page_size=1` on log lists (pathologically slow on the backend)

Helpers in [tests/integration/conftest.py](../../tests/integration/conftest.py):

- `log_list_kwargs()` — facade `.list(**log_list_kwargs())` → `max_pages` only
- `bounded_log_list_params()` — `ListParameters` for filters without `page_size`
- `assert_bounded_log_rows()` — assert row count within cap

List in the integration **`namespace` only** (no `traverse`).

## Checklist after changes

- [ ] LIST/GET covered via `test_resource_list_get_roundtrip.py` (or justified extras in `test_*.py`)
- [ ] Per-resource file only for unique behavior; create/update/delete where supported
- [ ] Update-not-supported resources have `NotImplementedError` test
- [ ] `uv run pytest tests/integration/resources/test_{resource}.py -v` passes with credentials
- [ ] OpenAPI quality gates pass when spec is present (`tests/unit/platform/core/test_openapi_spec.py`)

## Related

- [unit-tests.md](unit-tests.md) — Unit YAGNI / contract-vs-copy checklist
- [list-query-performance.md](list-query-performance.md) — Traverse, filters, pagination, slow lists
- [architecture.md](architecture.md) — Generated surface, overlay, custom facades
- [contracts.md](../contracts.md) — ListParameters, namespace, update_mask
- [endor-implement-sdk-resource](../../agent-knowledge/skills/endor-implement-sdk-resource/) — End-to-end skill (model-sync-first)
