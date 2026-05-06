# Generated Runtime Artifacts

This package contains generated artifacts consumed by runtime registry/facade
construction.

## What is generated

- `registry_contract.py` - generated runtime registry contract used by
  `endorlabs.registry`.
- `models/**` - mirrored generated model modules produced by model-sync.

## What is hand-maintained

- `__init__.py` may be created/updated by sync automation for package wiring.
- Any human-authored behavior changes should happen outside this package:
  - `src/endorlabs/registry_overlay.py` for explicit runtime policy overrides,
  - `devtools/model_sync_profiles/*.json` for sync profiles/overlays.

## Safe-edit policy

- Never hand-edit `registry_contract.py`.
- Never hand-edit files in `models/**`.
- Regenerate with:
  - `uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs`

## Cutover boundary

- Generated CRUD metadata/resources flow through the registry adapter.
- Manual custom facades remain explicit in `CUSTOM_FACADE_REGISTRY` (for example
  `ScanLogs`).

## Maintenance checklist for future agents

1. Run model-sync and verify runtime artifacts exist.
2. Verify `registry.py` resolves model and builder imports from generated
   contract metadata.
3. Verify parity/quality gates in unit tests and CI pass.
4. Update `devtools/model_sync_profiles/resource_descriptions.json` when adding a
   new resource description.
5. Keep this package generated-only; do not introduce handwritten runtime logic.
