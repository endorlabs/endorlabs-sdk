# API Validation Checklist

Pre-implementation validation for new Endor Labs resources. Complete
before writing any SDK code.

Spec: <https://api.endorlabs.com/download/openapiv2.swagger.json>
(schema drift workflow downloads to `.endorlabs-context/openapi.json` in CI).

---

## Phase 1: OpenAPI Analysis

- [ ] Find the service: grep the OpenAPI spec for `{Resource}Service` and endpoint paths
- [ ] Extract schema definitions: `v1{Resource}`, `v1{Resource}Spec`
- [ ] Document each field:
  - Required vs optional
  - Read-only fields (`readOnly: true`)
  - Field types and nested objects
  - Enum values where applicable
- [ ] Note the endpoint paths and HTTP methods:
  - LIST: `GET /v1/namespaces/{namespace}/{resource_name}`
  - GET: `GET /v1/namespaces/{namespace}/{resource_name}/{uuid}`
  - CREATE: `POST /v1/namespaces/{namespace}/{resource_name}`
  - UPDATE: `PATCH /v1/namespaces/{namespace}/{resource_name}`
  - DELETE: `DELETE /v1/namespaces/{namespace}/{resource_name}/{uuid}`

## Phase 2: Live Data Validation

- [ ] Run `endorctl api list -r {Resource} -n {namespace} --traverse`
  - Capture the full response JSON
  - Note actual fields present vs what the spec says
- [ ] Run `endorctl api get -r {Resource} -n {namespace} --uuid {uuid}`
  - Capture single resource response
  - Compare with the spec schema
- [ ] Note discrepancies:
  - Fields in live response not in spec ("extra" fields)
  - Fields in spec not in live response (may be optional or context-dependent)
  - Type mismatches between spec and actual data

## Phase 3: Implementation Matrix

Map fields into three categories:

### Universal fields (all resources)

- `uuid` (read-only)
- `tenant_meta.namespace`
- `meta.name`
- `meta.description`
- `meta.tags`
- `meta.create_time` (read-only)
- `meta.update_time` (read-only)

### Conditional fields (present in some resources)

- `context` (findings, scan results)
- `processing_status` (scan-generated resources)
- `index_data` (indexed resources)

### Resource-specific fields

Document all fields unique to this resource in `spec.*`.

### Operations matrix

| Operation | Supported | Notes |
|-----------|-----------|-------|
| LIST | yes/no | Filter, mask, traverse support |
| GET | yes/no | By UUID |
| CREATE | yes/no | Required payload fields |
| UPDATE | yes/no | update_mask required; mutable fields |
| DELETE | yes/no | Cascading behavior |

## References

- OpenAPI spec: <https://api.endorlabs.com/download/openapiv2.swagger.json>
- Conventions: `docs/conventions.md` (naming, spec path, list params, update_mask)
- Resource operations table: `docs/reference/resources.md`
- Create/update payloads: `docs/reference/create-update-payloads.md`
