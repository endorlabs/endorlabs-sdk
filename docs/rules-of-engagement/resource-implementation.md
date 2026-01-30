# Resource Implementation Rules of Engagement

Checklists for implementing new Endor Labs resources. Use BaseResourceOperations, one _get_*_ops() per module; return typed models. See [conventions.md](../conventions.md) for naming, spec path, list params, update_mask. Implement per `.cursor/rules/resource-patterns.mdc`.

## Phase 0: API Analysis (MANDATORY)

- [ ] Review OpenAPI spec for the resource (see [conventions.md](../conventions.md); spec at <https://api.endorlabs.com/download/openapiv2.swagger.json>).
- [ ] Note service name, URL endpoints, HTTP methods.
- [ ] Use live API responses as canonical structure; run endorctl list/get as needed.
- [ ] Confirm BaseResource compatibility; list_params (filter, mask, page_size, traverse) and update_mask support.

## Phase 1: Implementation

- [ ] Models: Meta, Spec, Resource extending BaseResource; schema drift detection per base.
- [ ] Operations: _get_*_ops(client) returning BaseResourceOperations(client, "resource-path", Model).
- [ ] List: accept list_params, max_pages; pass to ops.list(). Docstring: filter, mask, page_size, traverse.
- [ ] Get/Create/Update/Delete: pass through to ops; update accepts update_mask (comma-separated string → list). Namespace: update_mask required.
- [ ] Errors: use endorlabs.exceptions; log full response.text; no truncation.
- [ ] Add resource to RESOURCE_NAME_TO_TYPE and get_immutable_fields (in model_validation) if update is supported.
- [ ] Docstrings: Args, Returns, Raises so Pydantic/Pyright and IDE are self-explanatory; if a resource module lacks these, treat as a gap and add them.

## Phase 2: Expose on Client (optional)

If the resource should be available via the resource-oriented Client (e.g. `client.projects.list()`):

- [ ] Add one entry to the resource registry (e.g. `RESOURCE_REGISTRY` in `registry.py`): attr_name, module, model, list_fn, get_fn, create_fn, update_fn (or None), delete_fn (or None). See [architecture.md](architecture.md).
- [ ] Do not hand-wire the resource in `Client.__init__`; the registry drives which facades are attached.

No full code templates here; follow existing resource modules and [resource-patterns.mdc](../../.cursor/rules/resource-patterns.mdc).

