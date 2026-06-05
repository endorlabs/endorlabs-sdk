# Model-Sync Generation Modules

This package contains the canonical model-sync implementation used to keep SDK
surfaces synchronized with the OpenAPI spec while minimizing manual registry
maintenance.

## Module responsibilities

- `cli.py` - Orchestrates full sync flow and optional downstream generators.
- `path_safety.py` - Repo-root discovery and safe output paths for all writes.
- `policy.py` - Deterministic eligibility + partition policy (`x-internal`,
  aliases, entity extraction).
- `planner.py` - Builds deterministic shard plan in memory.
- `codegen.py` - In-process `datamodel_code_generator.generate()` per shard (RAM staging).
- `contract.py` - Builds facade/runtime contract and validates parity in memory.
- `provenance.py` - Hashing and provenance stamps embedded in committed artifacts.

## Generated outputs (committed ship surface only)

There is **no** persistent in-repo staging tree (`workspace/model-sync/`). Sync
holds plan, contract, and generated module source in RAM during the run.

Runtime-consumed generated files:

- `src/endorlabs/generated/registry_contract.py` (embeds `RUNTIME_REGISTRY_CONTRACT`)
- `src/endorlabs/generated/create_convenience.py`
- `src/endorlabs/generated/models/**`
- `src/endorlabs/client_surface.pyi` (via `--generate-stubs`)
- `docs/generated-reference/**` (via `--generate-reference-docs`)

## Regeneration commands

**Recommended (download latest public OpenAPI and regenerate stubs + reference docs):**

```bash
uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
```

**Regenerate using an already-downloaded spec** (repo root; spec at `.endorlabs-context/platform/openapi/openapiv2.swagger.json`):

```bash
uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
```

**Provenance watermark:** During generation, `endorctl_version` in generated file headers comes from the public **`GET /meta/version`** endpoint (same host as `--spec-url`), not from a local `endorctl` binary.

**Verify committed artifacts vs live upstream** (downloads OpenAPI + queries `meta/version`; no generation):

```bash
uv run python devtools/model_sync.py --verify-upstream-only
```

**Refresh only when stale** (if drift is detected, fetch OpenAPI and run full sync + stubs + reference docs):

```bash
uv run python devtools/model_sync.py --verify-and-sync-if-stale
```

Pre-push hooks and the **CI PR Main** lint job run `--verify-upstream-only` so pushes and
PRs fail when the public OpenAPI digest drifts from `registry_contract.py` provenance;
newer published endorctl versions log a warning without blocking.

**SHA-256 of the spec file only** (optional `--fetch-spec` first):

```bash
uv run python devtools/model_sync.py --spec-hash-only
```

Tooling inventory-only check (logs availability; no files written):

```bash
uv run python devtools/model_sync.py --inventory-only
```

## Edit policy

- Do not hand-edit `src/endorlabs/generated/registry_contract.py`.
- Do not hand-edit `src/endorlabs/generated/models/**`.
- Manual policy overrides belong in:
  - `src/endorlabs/registry_overlay.py` (runtime behavior overrides),
  - `devtools/model_sync_profiles/*.json` (policy/profile metadata),
  - tests + docs for explicit rationale.

## Determinism contract

Model sync is expected to be deterministic for identical spec + profiles:

- stable sorted JSON in embedded contract,
- stable runtime contract/resource ordering by `attr_name`,
- stable generated model modules for identical shard inputs.

## Triage map

- Contract validation errors during sync:
  - inspect `validate_contract_artifacts` output and `src/endorlabs/generated/registry_contract.py`.
- runtime import failures in `registry.py`:
  - check `registry_contract.py` import path fields.
- mutable/immutable update failures:
  - check contract `mutable_fields` / `immutable_fields` in `registry_contract.py`.
- stub description validation failures:
  - check `devtools/model_sync_profiles/resource_descriptions.json`.

## Shipped agent bundle (`src/endorlabs/agent_bundle/`)

Sync `agent-skills/` into the wheel bundle and regenerate `MANIFEST.json`:

```bash
uv run python devtools/sync_agent_bundle.py
uv run python devtools/sync_agent_bundle.py --verify
```

**When to run:** after editing any file under `agent-skills/`, or when adding/removing skills.

**Drift gate:** CI lint and pre-commit run `--verify` so committed bundle matches `agent-skills/`.

**Hand-maintained (not synced):** `INDEX.md`, `contracts/*.md`, `workflows/index.md` structure.

**Synced from `agent-skills/`:** `skills/` tree, `contracts/`, `INDEX.md`, and `MANIFEST.json` (schema-validated frontmatter; portable subset shipped in bundle `SKILL.md`).
