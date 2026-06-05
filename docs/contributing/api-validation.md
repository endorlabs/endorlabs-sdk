# API validation (contributing)

Spec-vs-wire checks before **overlay**, hand-written `resources/` modules, or integration tests. The SDK surface is normally **generated** by model sync; run regen first and read [generated-reference/resources.md](../generated-reference/resources.md) (and the per-resource page) for the operations matrix. Normative SDK behavior: [contracts.md](../contracts.md).

**OpenAPI:** `.endorlabs-context/platform/openapi/openapiv2.swagger.json` after `endorlabs.init()` or CI fetch; online: <https://api.endorlabs.com/download/openapiv2.swagger.json>.

## When to run this

- A new or changed resource appears in OpenAPI and you need to confirm list params, scope, or wire shape before editing [registry_overlay.py](../../src/endorlabs/registry_overlay.py) or `src/endorlabs/resources/`.
- Model sync regen succeeded but validation, integration tests, or endorctl samples disagree with the spec.
- **Not** a substitute for [docs-drift-workflow.md](docs-drift-workflow.md) (routine provenance/regen) or [architecture.md](architecture.md) (full contributor workflow).

## Phase 1: OpenAPI

- [ ] Grep the spec for `{Resource}Service` and namespace-scoped paths.
- [ ] Extract `v1{Resource}` and `v1{Resource}Spec`: required vs optional, `readOnly`, types, enums, nested objects.
- [ ] Confirm HTTP methods and paths (typical tenant resources):
  - LIST: `GET /v1/namespaces/{namespace}/{resource_name}`
  - GET: `GET /v1/namespaces/{namespace}/{resource_name}/{uuid}`
  - CREATE: `POST /v1/namespaces/{namespace}/{resource_name}`
  - UPDATE: `PATCH /v1/namespaces/{namespace}/{resource_name}/{uuid}` (or collection path per spec)
  - DELETE: `DELETE /v1/namespaces/{namespace}/{resource_name}/{uuid}`
- [ ] Note list parameters: `filter`, `mask`, `traverse`, pagination; note scope (`tenant` / `oss` / `system`) in generated [registry_contract.py](../../src/endorlabs/generated/registry_contract.py).

## Phase 2: Live data (optional, with credentials)

- [ ] `endorctl api list -r {Resource} -n {namespace}` in a namespace where data exists (match [integration-resource-tests.md](integration-resource-tests.md): **no `traverse`** unless you are explicitly validating tenant-wide behavior; see [namespace-traversal.md](namespace-traversal.md)).
- [ ] `endorctl api get -r {Resource} -n {namespace} --uuid {uuid}` when LIST returned a row.
- [ ] Compare wire JSON to OpenAPI: extra fields, missing optional fields, type mismatches (feeds overlay or model-sync profiles, not hand-built facades).

## Phase 3: Shape and operations

### Field buckets (spot-check)

| Bucket | Examples |
|--------|----------|
| Universal | `uuid`, `tenant_meta.namespace`, `meta.name`, `meta.description`, `meta.tags`, `meta.create_time`, `meta.update_time` |
| Conditional | `context` (findings, scan results), `processing_status`, `index_data` |
| Resource-specific | Remaining `spec.*` fields for this kind |

### Operations matrix (per resource)

| Operation | Supported | Notes |
|-----------|-----------|-------|
| LIST | yes/no | filter, mask, traverse; pagination cost — [list-query-performance.md](list-query-performance.md) |
| GET | yes/no | By UUID; pass resource object for namespace anchoring — [contracts.md](../contracts.md) |
| CREATE | yes/no | Required payload fields — [reference/create-update-payloads.md](../reference/create-update-payloads.md) |
| UPDATE | yes/no | `update_mask`; mutable vs immutable fields |
| DELETE | yes/no | Cascading behavior |

Prefer the generated registry row and [generated-reference/resources.md](../generated-reference/resources.md) over hand-maintaining this table.

## Related

- [architecture.md](architecture.md) — Regen, overlay, `resources/` deltas, integration tests
- [integration-resource-tests.md](integration-resource-tests.md) — Live API test order and log pagination profile
- [contracts.md](../contracts.md) — Naming, ListParameters, update_mask, namespace scoping
- [reference/resources.md](../reference/resources.md) — Landing page to generated resource matrix
