# Test and Spec Findings: Namespace, Warnings, Conftest

> **Purpose**: Document root-cause findings from spec research and endorctl validation. Clarify when the backend is to blame vs incorrect assertion, poor error handling, or SDK/URL mismatch.

## 1. Namespace Update: Backend vs SDK vs Spec

### OpenAPI spec

- **Paths defined**:
  - `PATCH /v1/namespaces/{object.tenant_meta.namespace}/namespaces` (collection; body: `NamespaceServiceUpdateNamespaceBody` with `object` and optional `request` with `update_mask`).
  - `PATCH /v1/namespaces/{object.tenant_meta.namespace}/namespaces/{object.uuid}/namespaces` (nested path with UUID).
- Spec describes **UpdateNamespace** and a 200 response; no 501 in the spec.

### endorctl validation

- **Command**: `endorctl api update -r Namespace -n <namespace> --uuid <uuid> -d '{"meta":{"description":"test"}}'`
- **Request**: endorctl sends **PATCH to the collection URL** `/v1/namespaces/<namespace>/namespaces` (no UUID in path).
- **Response**: **400** with message: `at least one fieldmask should be given.`
- So on the **collection** endpoint the backend **does** support namespace PATCH but **requires** a field mask. The error message is clear and correct.

### SDK behavior (after fix)

- **URL used**: `v1/namespaces/{tenant_meta_namespace}/namespaces` (collection; no UUID in path), aligned with spec and endorctl.
- **Body**: `{"object": payload_with_uuid, "request": {"update_mask": "..."}}`; `update_mask` is **required** (SDK raises `ValidationError` if missing).
- The SDK now matches the collection endpoint and sends an update mask; users get either success or a clear 400/ValidationError.

### Root cause

- **Not purely “backend wrong”**: On the collection endpoint the backend returns a clear **400** when the field mask is missing. On the path the SDK uses (resource with UUID), the backend may return **501** (not implemented for that path).
- **SDK/assertion/UX**:
  1. **URL mismatch**: SDK uses resource path; spec and endorctl use collection path for update. Aligning the SDK with the collection endpoint + `object` + `request.update_mask` (like other resources) would match the spec and endorctl and would yield either success or a clear 400 “fieldmask required” instead of 501.
  2. **Error handling**: If the backend returns 400 “at least one fieldmask should be given”, the SDK should map it to `ValidationError` and surface that message so the user knows to add an update mask.
  3. **Tests**: The namespace update test currently skips on 501. If the SDK is fixed to use the collection endpoint and send an update mask, the test could assert success or a clear validation error instead of assuming “API limitation”.

### Recommendation (implemented)

- **SDK fix applied**: Namespace update now uses the **collection** endpoint with `object` + `request.update_mask` (same pattern as findings/projects). `update_namespace(..., update_mask="meta.description")` is required; missing/empty mask raises `ValidationError` with a clear message.
- **Test**: Assert on success; skip only when the backend returns 501 in a given environment, or when `ValidationError` message contains "fieldmask" (backend contract differs).

- ~~Prefer fixing in **SDK** (and optionally **base**): implement namespace update via the **collection** endpoint with `object` + `request.update_mask` (same pattern as findings/projects). Then backend responses are either 200 or a clear 400 with message; no reliance on 501 for the “normal” path.
- **Test**: Keep skip only for environments where the backend truly does not support namespace PATCH; once SDK uses collection + mask, assert on success or on `ValidationError` with message containing “fieldmask”.

---

## 2. Warnings (pytest run)

- **Assumption check**: Warnings are not necessarily from “backend incorrectness”. They come from the **test run** (pytest, Pydantic, dependencies, or SDK code).
- **How to triage**:
  1. Run pytest **without** `--disable-warnings` and with `-W default` or `-W always` to see full warning text.
  2. Inspect stack traces to see whether the source is pytest, a library, or SDK (e.g. `endor_cockpit`).
  3. If the source is SDK code, fix the code or assertions; if it is a dependency, consider `filterwarnings` in **conftest** or pinning/upgrading the dependency.
- **Location for suppression**: Prefer **conftest** (e.g. `pytest_configure` or `filterwarnings`) for project-wide warning policy; per-test only when a single test intentionally triggers a warning.

---

## 3. Conftest vs Env: Namespace as Single Source

- **Current inconsistency**: Some tests use the `namespace` fixture from conftest; many set `self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.tgowan-endor")` in their own setup. The default is duplicated and can drift.
- **Best practice**: Treat **conftest** as the single source for “test namespace”:
  - Define a **single default** (e.g. `TEST_NAMESPACE_DEFAULT`) in conftest, used only there.
  - Provide a **`namespace`** fixture that returns `os.getenv("ENDOR_NAMESPACE", TEST_NAMESPACE_DEFAULT)` and skips if empty (when strict).
  - Tests that need a namespace should **use the `namespace` fixture** (or, if they must read env, use the same constant from conftest so the default is not duplicated).
- **Env-only option**: To rely only on env vars, do not set a default in conftest; the fixture returns `os.getenv("ENDOR_NAMESPACE")` and skips when unset. CI must set `ENDOR_NAMESPACE`.

---

## 4. Update contract (spec)

**Purpose**: Align SDK PATCH with API spec. All update-capable resources use collection URL and body shape `{ object, request?: { update_mask } }`.

### endorctl validation (assumptions)

Run locally (when endorctl and env are configured) to confirm API behavior:

- `endorctl api update --help` — shows `-n` (namespace), `-r` (resource), `--uuid`, `-d` (data), `--field-mask`.
- `endorctl api update -r Finding -n <namespace> --uuid <uuid> -d '{"meta":{"tags":["x"]}}' --field-mask meta.tags` — confirm collection URL and 200/400.
- `endorctl api update -r Namespace -n <namespace> --uuid <uuid> -d '{"meta":{"description":"test"}}'` — without field-mask yields 400 "at least one fieldmask should be given"; with `--field-mask meta.description` confirm 200 or 501 per environment.
- Optionally `endorctl api update -r Project -n <namespace> --uuid <uuid> -d '{"meta":{"description":"x"}}' --field-mask meta.description` — confirm collection PATCH contract.

**Deliverable**: Record which resources were tried, URL used (collection vs resource path), and response (200/400/501) so contract tests and SDK stay aligned.

### Spec checklist: update-capable resources

Every SDK resource that calls `ops.update()` has a PATCH path of the form `/v1/namespaces/{object.tenant_meta.namespace}/{resource_name}` (collection) and a body schema with `object` and `request` ($ref v1UpdateRequest). Read-only fields (from spec) drive immutable-field validation in the SDK.

| resource_name           | has_collection_patch | body_object_and_request | readOnly (spec; common + resource-specific) |
|-------------------------|----------------------|--------------------------|---------------------------------------------|
| findings                | yes                  | yes                      | uuid, meta.name, meta.create_time, meta.created_by, meta.update_time, meta.updated_by, spec.level, spec.project_uuid, spec.finding_metadata, tenant_meta.namespace |
| namespaces              | yes                  | yes                      | uuid, meta.name, meta.create_time, meta.created_by, meta.update_time, meta.updated_by, tenant_meta.namespace |
| projects                | yes                  | yes                      | uuid, meta.name, meta.create_time, meta.created_by, meta.update_time, meta.updated_by, spec.git, tenant_meta.namespace |
| policies                | yes                  | yes                      | uuid, meta.create_time, meta.created_by, meta.update_time, meta.updated_by, spec.policy_type, spec.template_uuid, tenant_meta.namespace |
| authorization-policies   | yes                  | yes                      | uuid, meta (v1Meta), **spec.is_support_policy**, tenant_meta.namespace |
| scan-profiles           | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| repositories            | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| repository-versions     | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| package-versions        | yes                  | yes                      | uuid, meta (v1Meta), **spec.ecosystem**, **spec.package_name**, **spec.internal_reference_key**, tenant_meta.namespace |
| metrics                 | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| linter-results          | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| dependency-metadata     | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| installations           | yes                  | yes                      | uuid, meta (v1Meta), **spec.external_name**, **spec.user**, **spec.ingestion_time**, **spec.target_type**, **spec.ingestion_token**, **spec.marked_for_deletion**, tenant_meta.namespace |
| package-licenses        | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |
| semgrep-rules           | yes                  | yes                      | uuid, meta (v1Meta), **spec.defined_by**, **spec.severity_level**, tenant_meta.namespace |
| scan-results            | yes                  | yes                      | uuid, meta (v1Meta readOnly), tenant_meta.namespace |

v1Meta readOnly (from OpenAPI): meta.create_time, meta.update_time, meta.upsert_time, meta.kind, meta.version, meta.created_by, meta.updated_by, meta.references, meta.index_data. Contract tests in `tests/test_base_update.py` assert PATCH URL (collection) and body shape (`object`; `request.update_mask` when mask provided).

### Field-mask check and mutable/immutable maps

- **All 16 update-capable resources** use `BaseResourceOperations.update()` and are in `RESOURCE_NAME_TO_TYPE`; every update with an `update_mask` gets the immutable-field check (block PATCH of read-only paths). UX is consistent: invalid mask paths raise `ValidationError` before the request.
- **Validated maps**: The 4 original types (findings, projects, policies, namespaces) have **spec-derived** immutable (and mutable) lists with resource-specific fields (e.g. `spec.level`, `spec.project_uuid` for findings; `spec.policy_type`, `spec.template_uuid` for policies). The other 12 resources use the **v1Meta-derived** common set (uuid, meta timestamps/audit/kind/version/references/index_data, tenant_meta.namespace). Add resource-specific `readOnly` from each resource’s Update body/spec in OpenAPI when needed for stricter validation.

---

## 5. CI: read-only credentials and local marker

**Assumption**: CI runs integration tests with **read-only** API credentials. Admin/write keys are not used in CI/CD.

- **Marker**: Any test that calls create, update, or delete must be marked `@pytest.mark.local` so it is excluded from CI (`pytest -m "integration and not local"`).
- **Rationale**: Write operations require elevated permissions; with read-only credentials they return 403. Marking them local keeps CI green without storing admin keys in secrets.
- **Run local tests**: Use API credentials with write access and run `pytest -m "integration"` (or omit the filter) to include local tests.

---

## 6. References

- OpenAPI: <https://api.endorlabs.com/download/openapiv2.swagger.json> (paths for namespaces, `NamespaceServiceUpdateNamespaceBody`, `v1UpdateRequest`).
- SDK: `src/endor_cockpit/resources/namespace.py` (`update_namespace`), `src/endor_cockpit/models/base.py` (update with mask).
- Troubleshooting: [troubleshooting.md](troubleshooting.md).
