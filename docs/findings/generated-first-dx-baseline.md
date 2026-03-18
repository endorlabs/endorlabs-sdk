# Generated-First DX Baseline

This baseline defines the acceptance thresholds used by the generated-first cutover gates.

## Scope

Representative resources:
- `project`
- `finding`
- `policy`
- `repository`
- `scan_result`

Dimensions:
- Nested type depth (no dominant `RootModel[Any]` wrappers for core payload trees)
- Enum coverage
- Validator/normalization behavior
- Mutability metadata (`mutable_fields` / `immutable_fields`)
- Convenience workflow support (create mode, update mask semantics, tag workflow flags)

## Baseline Matrix (Current)

| Dimension | Hand-crafted resources | Generated-first contract/models | Baseline status |
|---|---|---|---|
| Nested type depth | Strong for selected modeled resources | Mixed; improved by transitive schema ref closure | Needs closure |
| Enum coverage | Strong | Partial/varies by schema shard | Needs closure |
| Validator behavior | Resource-specific normalization present | Limited; mostly schema-derived | Needs closure |
| Mutability metadata | Available via class helpers | Available in generated contract/runtime index | On track |
| Workflow metadata | Implicit/manual behavior | Explicit generated `create_mode`, `update_requires_mask`, `workflow_flags` | On track |
| Facade docstrings/IntelliSense | Strong and curated | Generated + overlay; capability metadata now included in stub docs | On track |

## Gate Thresholds

Gate progression thresholds for the selected resources:
- `type-depth`: No selected resource may regress versus baseline; at least 3/5 must improve.
- `enum-coverage`: No selected resource may lose enum exposure already present in generated output.
- `mutability`: 100% of selected resources must have generated mutability metadata in runtime contract.
- `workflow-capability`: 100% of selected resources must emit capability metadata and be consumed by stub/docs generation.
- `crud-regression`: Existing unit CRUD subset must remain green.

## Verification Commands

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pyright`
- `uv run pytest tests/unit/tooling/scripts/ -x`
- `uv run pytest tests/unit/client/ -x`
