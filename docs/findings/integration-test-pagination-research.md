# Integration Test Pagination & Configuration Research

Findings from reviewing test configuration and pagination patterns across the integration test suite.

Status note: this document captures a point-in-time audit. Enforced conventions now live in `tests/unit/test_integration_pagination_guard.py` and `tests/conftest.py`.

## 1. Conftest configuration

### `tests/conftest.py`

- **Constants (single source for list limits):**
  - `TEST_PAGE_SIZE = 1`
  - `TEST_MAX_PAGES = 1`
  - `TEST_TRAVERSE_PAGE_SIZE = 1`
  - `TEST_MAX_PAGES_TRAVERSE = 1`
- **Namespace:** `TEST_NAMESPACE_DEFAULT` (env `ENDOR_NAMESPACE` or default).
- **Cleanup constants:** `DEFAULT_TEST_TAGS`, `TEST_API_KEY_NAMESPACE`, prefixes for scan profiles, namespaces, semgrep rules, etc. (used by cleanup scripts, not by tests for pagination).
- **Fixtures:** `setup_logging` (autouse).

### `tests/integration/conftest.py`

- **Imports:** Only `TEST_NAMESPACE_DEFAULT` from `tests.conftest` (does **not** re-export pagination constants).
- **Fixtures:** `api_client`, `api_client_fast_retry`, `namespace`, `root_namespace`, `endor_client`, `endor_root_client`, `integration_config`, `requires_credentials`, `requires_endorctl`.
- **Collection:** Marks all tests under `integration` with `@pytest.mark.integration` and skips them when credentials are missing.
- **Pagination:** No pagination constants defined here; tests that need them import from `tests.conftest`.

### `tests/integration/resources/conftest.py`

- **ResourceTestBase mixin:** Provides `setup_resource` (autouse) wiring `client`, `namespace`, `root_namespace`, `created_uuids` and calling `_cleanup()`. No pagination constants.

---

## 2. Findings by file

### `tests/integration/resources/`

| File | page_size | max_pages | Uses conftest constants? | traverse tests use _TRAVERSE? | Notes |
|------|-----------|-----------|---------------------------|-------------------------------|--------|
| **test_api_key.py** | — | ✓ | `TEST_MAX_PAGES_TRAVERSE` only | ✓ | No `list_params`; list calls use `traverse=True, max_pages=TEST_MAX_PAGES_TRAVERSE`. |
| **test_audit_log.py** | ✓ | ✓ | `TEST_PAGE_SIZE`, `TEST_MAX_PAGES`, `TEST_MAX_PAGES_TRAVERSE`, `TEST_TRAVERSE_PAGE_SIZE` | ✓ | Setup: `ListParameters(page_size=TEST_PAGE_SIZE)`, `max_pages=TEST_MAX_PAGES`. List/GET: `TEST_MAX_PAGES_TRAVERSE`. |
| **test_authentication_log.py** | — | ✓ | `TEST_MAX_PAGES_TRAVERSE` only | ✓ | No list_params; all list calls use `traverse=True, max_pages=TEST_MAX_PAGES_TRAVERSE`. |
| **test_authorization_policy.py** | (not read in detail) | — | — | — | — |
| **test_dependency_metadata.py** | ✓ | ✓ | `TEST_MAX_PAGES_TRAVERSE`, `TEST_PAGE_SIZE`, `TEST_TRAVERSE_PAGE_SIZE` | ✓ | Fixture uses `ListParameters(page_size=TEST_TRAVERSE_PAGE_SIZE, traverse=True)`, `max_pages=TEST_MAX_PAGES_TRAVERSE`. |
| **test_endor_license.py** | — | ✓ | `TEST_MAX_PAGES_TRAVERSE` only | ✓ | No list_params; all list calls use `traverse=True, max_pages=TEST_MAX_PAGES_TRAVERSE`. |
| **test_finding.py** | ✓ | ✓ | `TEST_PAGE_SIZE`, `TEST_MAX_PAGES`, `TEST_MAX_PAGES_TRAVERSE` | ✓ | Setup fixture: `ListParameters(page_size=TEST_PAGE_SIZE)`, `max_pages=TEST_MAX_PAGES`. One test: `finding.list(max_pages=TEST_MAX_PAGES)` (no traverse). |
| **test_finding_log.py** | ✓ | ✓ | All four constants | ✓ | List/GET use `traverse=True, max_pages=TEST_MAX_PAGES_TRAVERSE`. |
| **test_installation.py** | ✓ | ✓ | `TEST_MAX_PAGES`, `TEST_MAX_PAGES_TRAVERSE`, `TEST_PAGE_SIZE` | ✓ (list/get) | **Issue:** `sample_installation` uses `traverse=True` with `page_size=TEST_PAGE_SIZE` and `max_pages=TEST_MAX_PAGES` (should use TRAVERSE variants for consistency). **Issue:** `test_installation_filter_by_platform` calls `.list(list_params=list_params)` **with no `max_pages`** — can fetch all pages, timeout risk. |
| **test_linter_result.py** | ✓ | ✓ | `TEST_MAX_PAGES_TRAVERSE`, `TEST_PAGE_SIZE`, `TEST_TRAVERSE_PAGE_SIZE` | ✓ | Filter test uses `list_params` with filter + `max_pages=TEST_MAX_PAGES_TRAVERSE` (no traverse in list_params; list is under single namespace). |
| **test_metric.py** | ✓ | ✓ | All four | ✓ (list/get), mixed in setup | **Inconsistency:** `sample_metric` uses `ListParameters(traverse=True, page_size=TEST_PAGE_SIZE)` and `max_pages=TEST_MAX_PAGES`; traverse calls should use TRAVERSE constants. Filter test correctly uses `TEST_TRAVERSE_PAGE_SIZE` and `TEST_MAX_PAGES_TRAVERSE`. |
| **test_namespace.py** | — | mixed | `TEST_MAX_PAGES_TRAVERSE` + **hardcoded 10** | ✓ (except one) | **Issue:** In `test_namespace_create` (cleanup list), `root_client.namespace.list(traverse=True, max_pages=10)` — only place using a **hardcoded** max_pages instead of a constant. Rest use `TEST_MAX_PAGES_TRAVERSE`. |
| **test_package_version.py** | ✓ | ✓ | All four | ✓ | Setup fixture: non-traverse with `TEST_PAGE_SIZE`/`TEST_MAX_PAGES`. One test: `package_version.list(max_pages=TEST_MAX_PAGES)` (no traverse). |
| **test_policy.py** | ✓ | ✓ | All four | ✓ | Setup: non-traverse. One test: `policy.list(max_pages=TEST_MAX_PAGES)` (no traverse). |
| **test_policy_template.py** | — | ✓ | `TEST_MAX_PAGES_TRAVERSE` only | ✓ | No list_params. |
| **test_project.py** | ✓ | ✓ | All four | ✓ | Setup: non-traverse. Filter/mask tests: `TEST_PAGE_SIZE`, `TEST_MAX_PAGES`. One test: `project.list(max_pages=TEST_MAX_PAGES)` (no traverse). |
| **test_repository.py** | ✓ | ✓ | All four | ✓ (mostly) | **Issue:** `sample_repository` uses `ListParameters(page_size=TEST_PAGE_SIZE, traverse=True)` with `max_pages=TEST_MAX_PAGES` — traverse should use `TEST_MAX_PAGES_TRAVERSE`. **Issue:** `test_repository_update_client_ux` uses `repository.list(traverse=True, max_pages=TEST_MAX_PAGES)` — should use `TEST_MAX_PAGES_TRAVERSE` when traverse=True. Filter/mask tests use `TEST_MAX_PAGES` with traverse in list_params (debatable: filter narrows result set). |
| **test_repository_version.py** | ✓ | ✓ | All four | ✓ | Setup: non-traverse. Filter/mask and one UX test use `TEST_MAX_PAGES` (no traverse in that UX test). |
| **test_scan_log_request.py** | ✓ | ✓ | `TEST_MAX_PAGES`, `TEST_MAX_PAGES_TRAVERSE`, `TEST_PAGE_SIZE` | ✓ | `sample_scan_result`: traverse list with `page_size=TEST_PAGE_SIZE`, `max_pages=TEST_MAX_PAGES_TRAVERSE` (could use `TEST_TRAVERSE_PAGE_SIZE` for consistency). Namespace list: `traverse=True`, `TEST_PAGE_SIZE`, `TEST_MAX_PAGES` (traverse with non-TRAVERSE max_pages). |
| **test_scan_profile.py** | ✓ | ✓ | `TEST_MAX_PAGES`, `TEST_MAX_PAGES_TRAVERSE`, `TEST_PAGE_SIZE` | ✓ | Setup: non-traverse. Filter/mask: non-traverse, `TEST_PAGE_SIZE`, `TEST_MAX_PAGES`. |
| **test_scan_result.py** | ✓ | ✓ | All four | ✓ | Setup uses `TEST_TRAVERSE_PAGE_SIZE` and `TEST_MAX_PAGES_TRAVERSE`. Filter test uses `list_params` with filter (no traverse), `TEST_PAGE_SIZE`, `max_pages=TEST_MAX_PAGES_TRAVERSE`. |
| **test_semgrep_rule.py** | — | ✓ | `TEST_MAX_PAGES_TRAVERSE` only | ✓ | No list_params. |
| **test_* (others)** | — | — | — | — | authorization_policy, code_owners, invitation, notification_target, scan_workflow, version_upgrade not fully enumerated; same patterns expected. |

### `tests/integration/workflows/`

| File | page_size | max_pages | Uses conftest constants? | traverse use _TRAVERSE? | Notes |
|------|-----------|-----------|---------------------------|-------------------------|--------|
| **test_retrieving_scan_results.py** | ✓ | ✓ | All four | Mixed | **Issue:** `_get_most_recent_scan_result` uses `traverse=True` with `page_size=TEST_PAGE_SIZE` and `max_pages=TEST_MAX_PAGES` — should use `TEST_TRAVERSE_PAGE_SIZE` and `TEST_MAX_PAGES_TRAVERSE`. **Issue (timeout risk):** `_get_findings_directly` calls `finding.list(list_params=list_params)` **with no `max_pages`** — can iterate all pages on large tenants. Rest of workflow uses TRAVERSE constants correctly. |

### `tests/integration/client/`

| File | page_size | max_pages | Uses conftest constants? | traverse use _TRAVERSE? | Notes |
|------|-----------|-----------|---------------------------|-------------------------|--------|
| **test_concurrent_list.py** | — | ✓ | `TEST_MAX_PAGES` only | **No** | **Inconsistency:** Both `test_concurrent_list_projects_returns_results` and `test_concurrent_list_with_filter` use `traverse=True` with `max_pages=TEST_MAX_PAGES`. For traverse, the suite standard is `TEST_MAX_PAGES_TRAVERSE`. Performance test uses hardcoded `max_pages=2` (intentional for timing). |

---

## 3. ListParameters with filters and timeout risk

- **test_installation.py — `test_installation_filter_by_platform`**  
  `ListParameters(filter=..., traverse=True)` passed to `installation.list(list_params=list_params)` **with no `max_pages`**. On large tenants this can request many pages and contribute to API-side timeouts.  
  **Recommendation:** Add `max_pages=TEST_MAX_PAGES_TRAVERSE` (and optionally `page_size=TEST_TRAVERSE_PAGE_SIZE` in list_params).

- **test_retrieving_scan_results.py — `_get_findings_directly`**  
  `ListParameters(filter=f'spec.project_uuid=="{project_uuid}"', traverse=True)` passed to `finding.list(list_params=list_params)` **with no `max_pages`**. Same risk for large datasets.  
  **Recommendation:** Add `max_pages=TEST_MAX_PAGES_TRAVERSE` (and optionally `page_size=TEST_TRAVERSE_PAGE_SIZE` in list_params).

- **Other filter tests** (e.g. linter_result, metric, scan_result, repository, project) pass `max_pages` (either `TEST_MAX_PAGES` or `TEST_MAX_PAGES_TRAVERSE`) and are bounded.

---

## 4. Summary of inconsistencies and issues

1. **Traverse with non-TRAVERSE constants**
   - **test_repository.py:** `sample_repository` uses `max_pages=TEST_MAX_PAGES` with `traverse=True`; `test_repository_update_client_ux` uses `traverse=True, max_pages=TEST_MAX_PAGES`. Should use `TEST_MAX_PAGES_TRAVERSE` (and optionally `TEST_TRAVERSE_PAGE_SIZE` where list_params are used).
   - **test_concurrent_list.py:** Both concurrent list tests use `traverse=True, max_pages=TEST_MAX_PAGES`. Should use `TEST_MAX_PAGES_TRAVERSE`.
   - **test_retrieving_scan_results.py:** `_get_most_recent_scan_result` uses `page_size=TEST_PAGE_SIZE`, `max_pages=TEST_MAX_PAGES` with traverse. Should use TRAVERSE constants.
   - **test_installation.py:** `sample_installation` uses `page_size=TEST_PAGE_SIZE`, `max_pages=TEST_MAX_PAGES` with traverse. Prefer TRAVERSE constants.
   - **test_metric.py:** `sample_metric` uses `page_size=TEST_PAGE_SIZE`, `max_pages=TEST_MAX_PAGES` with traverse. Prefer TRAVERSE constants.
   - **test_scan_log_request.py:** Namespace list uses `traverse=True` with `max_pages=TEST_MAX_PAGES`; could use `TEST_MAX_PAGES_TRAVERSE` for consistency.

2. **Hardcoded pagination**
   - **test_namespace.py:** `max_pages=10` in `test_namespace_create` (list after create). Only hardcoded value in integration list calls. Consider `TEST_MAX_PAGES_TRAVERSE` or a named constant (e.g. `TEST_MAX_PAGES_LIST_AFTER_CREATE`) if 10 is intentional.

3. **Missing max_pages (timeout risk)**
   - **test_installation.py:** `test_installation_filter_by_platform` — add `max_pages=TEST_MAX_PAGES_TRAVERSE`.
   - **test_retrieving_scan_results.py:** `_get_findings_directly` — add `max_pages=TEST_MAX_PAGES_TRAVERSE`.

4. **Optional consistency (non-blocking)**
   - Several places use `TEST_PAGE_SIZE` inside `ListParameters` for traverse lists; the suite standard is `TEST_TRAVERSE_PAGE_SIZE` for traverse. Currently both are 1, so behavior is the same; aligning to TRAVERSE constant would make intent clear and future-proof.

---

## 5. Recommended convention (for future tests)

- **Non-traverse list:** `page_size=TEST_PAGE_SIZE`, `max_pages=TEST_MAX_PAGES` (or via `ListParameters(page_size=TEST_PAGE_SIZE)` + `max_pages=TEST_MAX_PAGES`).
- **Traverse list:** `page_size=TEST_TRAVERSE_PAGE_SIZE` (in list_params when used), `max_pages=TEST_MAX_PAGES_TRAVERSE`.
- **Any `.list(...)` call:** Always pass an explicit `max_pages` to avoid unbounded iteration and API timeouts.
- **Filter/sort with traverse:** Same as traverse list; use TRAVERSE constants and always set `max_pages`.
