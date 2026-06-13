# Generated Reference

These files are generated. Do not hand-edit.

## Regenerate

```bash
uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
uv run python devtools/generate_route_contract.py
```

Or standalone:

- `uv run python devtools/generate_reference_docs.py` — matrices, `api-surfaces.md`, per-resource pages
- `uv run python devtools/generate_route_contract.py` — `route_contract.py`, `resource-routes.md`

## Contents

| File | Source |
|------|--------|
| [resources.md](resources.md) | Registry + OpenAPI op matrix |
| [api-surfaces.md](api-surfaces.md) | Exports, CRUD signatures, accessors, custom facades |
| [resource-routes.md](resource-routes.md) | Relationship accessor edge table |
| [create-update-payloads.md](create-update-payloads.md) | Create/update payload matrices |
| [resources/](resources/README.md) | Per-resource CRUD + facade helper sections |
| [coverage.json](coverage.json) | Machine-readable coverage metadata |

Normative usage patterns: [guides/facade-helpers.md](../guides/facade-helpers.md).

CI drift gate: `devtools/verify_ship_artifacts.py`.
