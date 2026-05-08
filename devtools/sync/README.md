# Model-Sync Generation Modules

This package contains the canonical model-sync implementation used to keep SDK
surfaces synchronized with the OpenAPI spec while minimizing manual registry
maintenance.

## Module responsibilities

- `cli.py` - Orchestrates full sync flow and optional downstream generators.
- `policy.py` - Deterministic eligibility + partition policy (`x-internal`,
  aliases, entity extraction).
- `planner.py` - Builds deterministic shard plan and mapping metadata.
- `codegen.py` - Runs `datamodel-codegen` for shard modules and tracks progress.
- `contract.py` - Builds facade/runtime contract, parity, payload, operation, and
  runtime index metadata.
- `provenance.py` - Hashing, toolchain/provenance stamps, and artifacts manifest.

## Generated outputs

Primary outputs live under `workspace/model-sync/custom_mapping/`:

- `mapping/entity_mapping.json`
- `mapping/operation_path_metadata.json`
- `mapping/payload_schemas.json`
- `mapping/registry_parity_report.json`
- `mapping/runtime_index.json`
- `facade_contract.json`
- `artifacts_manifest.json`

Runtime-consumed generated files:

- `src/endorlabs/generated/registry_contract.py`
- `src/endorlabs/generated/models/**` (mirrored generated model modules)

## Regeneration commands

**Recommended (download latest public OpenAPI, regenerate, print compact delta vs default branch):**

```bash
uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs --delta-summary
```

Same on PowerShell.

**Regenerate using an already-downloaded spec** (repo root; spec at `.endorlabs-context/openapiv2.swagger.json`):

```bash
uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
```

**Verify committed artifacts vs live upstream** (downloads OpenAPI + queries `meta/version`; no generation):

```bash
uv run python devtools/model_sync.py --verify-upstream-only
```

**Refresh only when stale** (if drift is detected, fetch OpenAPI and run full sync + stubs + reference docs):

```bash
uv run python devtools/model_sync.py --verify-and-sync-if-stale
```

Pre-push hooks run `--verify-upstream-only` so pushes fail when the public OpenAPI digest
drifts from `registry_contract.py` provenance; newer published endorctl versions log a
warning without blocking.

**SHA-256 of the spec file only** (optional `--fetch-spec` first):

```bash
uv run python devtools/model_sync.py --spec-hash-only
```

**Compact delta only** (after a sync; baseline = `origin/main` / `main` / … when available):

```bash
uv run python devtools/model_sync_pr_deltas.py --auto-baseline --print-summary
```

**Full narrative delta** (upstream + resources + provenance markdown):

```bash
uv run python devtools/model_sync_pr_deltas.py --auto-baseline --print-all-markdown
```

Tooling inventory-only check:

```bash
uv run python devtools/model_sync.py --inventory-only
```

## Edit policy

- Do not hand-edit generated files under `workspace/model-sync/custom_mapping/`.
- Do not hand-edit `src/endorlabs/generated/registry_contract.py`.
- Do not hand-edit `src/endorlabs/generated/models/**`.
- Manual policy overrides belong in:
  - `src/endorlabs/registry_overlay.py` (runtime behavior overrides),
  - `devtools/model_sync_profiles/*.json` (policy/profile metadata),
  - tests + docs for explicit rationale.

## Determinism contract

Model sync is expected to be deterministic for identical spec + profiles:

- stable sorted JSON output (keys and arrays),
- stable runtime contract/resource ordering by `attr_name`,
- stable artifacts manifest hash from generated files.

## Triage map

- `registry_parity_report.status=fail`:
  - check `mapping/missing_in_mapping`, then `devtools/sync/policy.py` aliases.
- runtime import failures in `registry.py`:
  - check `facade_contract.json` import path fields and `mapping/runtime_index.json`.
- mutable/immutable update failures:
  - check `facade_contract.json` `mutable_fields` / `immutable_fields`.
- stub description validation failures:
  - check `devtools/model_sync_profiles/resource_descriptions.json`.
