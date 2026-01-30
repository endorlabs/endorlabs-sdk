# Resource Implementation Rules of Engagement

Checklists for implementing new Endor Labs resources. Use BaseResourceOperations, one _get_*_ops() per module; return typed models. See [conventions.md](../conventions.md) for naming, spec path, list params, update_mask. Implement per `.cursor/rules/resource-patterns.mdc`.

## Phase 0: API Analysis (MANDATORY)

- [ ] Review OpenAPI spec: `external_docs/openapi-swagger.json` for the resource (see [conventions.md](../conventions.md)).
- [ ] Note service name, URL endpoints, HTTP methods.
- [ ] Use live API responses as canonical structure; run endorctl list/get as needed.
- [ ] Confirm BaseResource compatibility; list_params (filter, mask, page_size, traverse) and update_mask support.

## Phase 1: Implementation

- [ ] Models: Meta, Spec, Resource extending BaseResource; schema drift detection per base.
- [ ] Operations: _get_*_ops(client) returning BaseResourceOperations(client, "resource-path", Model).
- [ ] List: accept list_params, max_pages; pass to ops.list(). Docstring: filter, mask, page_size, traverse.
- [ ] Get/Create/Update/Delete: pass through to ops; update accepts update_mask (comma-separated string → list). Namespace: update_mask required.
- [ ] Errors: use endor_cockpit.exceptions; log full response.text; no truncation.
- [ ] Add resource to RESOURCE_NAME_TO_TYPE and get_immutable_fields (in model_validation) if update is supported.

No full code templates here; follow existing resource modules and [resource-patterns.mdc](../../.cursor/rules/resource-patterns.mdc).
