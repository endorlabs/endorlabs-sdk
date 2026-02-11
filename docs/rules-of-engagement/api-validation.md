# API Validation Rules of Engagement

Pre-implementation validation. Spec: see [conventions.md](../conventions.md) (OpenAPI URL; workflow downloads to `.endorlabs-context/` in CI).

## Phase 1: OpenAPI

- [ ] Find service: grep OpenAPI spec for {Resource}Service and endpoint paths.
- [ ] Extract schema: v1{Resource}, v1{Resource}Spec (required vs optional, readOnly).
- [ ] Document required/optional/read-only fields and types.

## Phase 2: Live data

- [ ] Run endorctl api list -r {Resource} (and get if needed); capture response shape.
- [ ] Compare with OpenAPI; note any extra or missing fields.

## Phase 3: Implementation matrix

- [ ] Map universal fields, conditional fields, resource-specific fields.
- [ ] Confirm which CRUD operations and list params (filter, mask, traverse) the API supports.

Use conventions.md for spec path and list/update patterns.
