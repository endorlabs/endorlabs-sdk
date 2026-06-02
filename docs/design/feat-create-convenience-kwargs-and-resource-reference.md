# Plan: Create convenience kwargs (Side A) and per-resource reference docs (Side B)

**Branch:** `feat/create-convenience-kwargs-and-resource-docs`
**Status:** Planning (not implemented on this commit)
**Normative contracts:** Update [contracts.md](../contracts.md) when behavior ships; this doc is implementation planning only.

## Problem

1. **Side A — Runtime / typing:** OpenAPI defines writable `spec` fields (e.g. `metadata_filter` on `v1VectorStoreQuerySpec`), but hand-written `build_create_payload` only promotes a manual `spec_fields` tuple. Unlisted flat kwargs are **silently dropped**. Facade `create()` is typed as `**kwargs: Any` in `client_surface.pyi`, so Pyright and agents on PyPI cannot discover spec fields.
2. **Side B — Discoverability:** Generated reference is three aggregate matrices (`resources.md`, `create-update-payloads.md`, `api-surfaces.md`) plus `coverage.json`. There is no per-resource page tying `client.VectorStoreQuery` → create shape → response `spec.matches` → related resources. `src/endorlabs/generated/models/` is organized by OpenAPI service shards, not SDK `attr_name`.

## Goals

| ID | Goal |
|----|------|
| G1 | Writable OpenAPI `spec` properties are promotable as flat `create()` kwargs (generated list, not hand-maintained per resource). |
| G2 | Unknown flat create kwargs are never silently ignored (`TypeError` or explicit allowlist). |
| G3 | `client_surface.pyi` exposes per-resource `create()` signatures for resources with `create_mode=both` and a builder. |
| G4 | One generated markdown page per facade resource under `docs/generated-reference/resources/`. |
| G5 | Agent index: `src/endorlabs/generated/README.md` + optional wheel-shipped JSON index. |

## Non-goals

- Reorganizing `src/endorlabs/generated/models/` into per-SDK-resource Python packages (fights model-sync; wrong axis).
- Replacing hand-written `src/endorlabs/resources/*.py` models with generated types for facade return types.
- Documenting all 215 model-sync entities; only **registry facade resources** (~41).
- `VectorStoreMetadataQuery` facade (not in SDK registry today).

---

## Side A — Runtime and typing

### A1. Extract create convenience fields from OpenAPI (model-sync)

**Where:** `devtools/sync/contract.py` — extend `build_payload_schemas()` or add `build_create_convenience_metadata()`.

**Algorithm (per `ResourceEntry` with create):**

1. Resolve create body definition(s) from existing `create_payload_definitions` (e.g. `VectorStoreQueryServiceCreateVectorStoreQueryBody`).
2. Locate `spec` `$ref` → `v1*Spec` definition.
3. Collect property names where `readOnly` is not true.
4. Split:
   - **`create_convenience_spec_fields`:** spec properties (ordered: required first, then optional).
   - **`create_convenience_meta_fields`:** top-level body properties that map to create meta (typically `meta.name` paths only when `meta` is optional on wire; align with existing builders that inject default `name`).
5. Exclude response-only spec fields already marked `readOnly` in OpenAPI (e.g. `matches` on `v1VectorStoreQuerySpec`).

**Output artifacts:**

| Artifact | Location |
|----------|----------|
| Extended payload metadata | `workspace/model-sync/custom_mapping/mapping/payload_schemas.json` (new keys per resource) |
| Registry contract field | `src/endorlabs/generated/registry_contract.py` — `create_convenience_spec_fields`, `create_convenience_meta_fields` (nullable lists) |

**Registry adapter:** `src/endorlabs/registry.py` — expose on `ResourceEntry` for stub generator and docs.

**Overlay:** `src/endorlabs/registry_overlay.py` — allow manual overrides only when OpenAPI is wrong (document in overlay comment).

### A2. Shared payload promotion helper

**Where:** `src/endorlabs/utils/create_payload.py` (new) or `src/endorlabs/resources/_create_payload.py`.

```text
promote_create_kwargs(
    payload_kwargs: dict[str, Any],
    *,
    spec_fields: Sequence[str],
    meta_defaults: dict[str, Any] | None = None,
    meta_field_map: dict[str, str] | None = None,  # e.g. name -> meta.name
) -> dict[str, Any]
```

**Behavior:**

- If `spec` not in kwargs: build `spec` from keys in `spec_fields` present in kwargs; remove those keys from top level.
- If `meta` not in kwargs: apply `meta_defaults` / `meta_field_map` (e.g. `name` → `meta.name`).
- After promotion: if any remaining keys are not `namespace`, `payload`, or known meta aliases → **`TypeError`** with resource hint (G2).

**Migration:** Refactor hand-written `build_create_payload` functions to call helper with generated field list from registry metadata **or** keep local wrappers that pass resource-specific lists imported from generated contract constants.

**Preferred long-term:** model-sync emits `src/endorlabs/generated/create_convenience.py` with per-resource tuples/constants consumed by thin `build_create_payload` in `resources/` (avoids importing registry at module load in resources).

### A3. Hand-written resource alignment

**Pilot:** `vector_store_query.py`

- Add typed `metadata_filter: dict[str, Any] | None` on `VectorStoreQuerySpec`.
- Use promoted fields from generated constants.
- Extend drift `known` set: `metadata_filter`, `matches`.

**Rollout:** Batch-update all resources with `build_create_payload` + `create_mode=both` (grep `spec_fields =`); prioritize create-only query resources (`QueryVulnerability`, `QueryMalware`, `VectorStoreQuery`, …).

### A4. Stub generator — typed `create()` per resource

**Where:** `devtools/generate_client_stub.py`

For each `ResourceEntry` with `create` in `supported_ops` and `create_mode == "both"`:

- Emit override on `_<AttrName>Facade`:

```python
def create(
    self,
    payload: CreateVectorStoreQueryPayload | None = None,
    *,
    name: str | None = ...,
    namespace: str | None = ...,
    vector_store_uuid: str = ...,
    query: str = ...,
    metadata_filter: dict[str, Any] | None = ...,
) -> VectorStoreQuery: ...
```

- Required vs optional from OpenAPI `required` arrays on spec.
- Resources without generated lists keep `**kwargs: Any` until metadata exists.

**CI:** Existing `client_surface.pyi` diff check in `.github/workflows/ci-pr-main.yml`.

### A5. Contracts and consumer UX docs

Update when shipping:

- [contracts.md](../contracts.md) — create convenience kwargs SHALL match generated writable spec/meta lists; unknown kwargs MUST error.
- [consumer-ux-list-update.md](../guides/consumer-ux-list-update.md) — link to per-resource generated pages.

---

## Side B — Per-resource generated reference

### B1. Generator extension

**Where:** `devtools/generate_reference_docs.py` (or `devtools/generate_resource_reference_pages.py` called from model-sync).

**Output layout:**

```text
docs/generated-reference/
  resources.md              # existing matrix (keep)
  resources/
    README.md               # index table: attr_name -> page, path, scope, ops
    VectorStoreQuery.md
    Project.md
    ...
  index.json                # optional: same metadata for agents
```

**Per-page sections (generated):**

1. Title + one-line description (`resource_descriptions.json` + model docstring).
2. Client access: `client.<AttrName>`, `resource_name`, scope, parent.
3. Operations table (from registry + OpenAPI).
4. **Create** — payload model (hand-written import path), required/optional **top-level** and **spec** fields from `payload_schemas` + hand-written Pydantic inspection fallback.
5. **Create convenience kwargs** — flat kwargs list (Side A output).
6. **Response / read-only spec fields** — e.g. `matches`.
7. **Examples** — minimal `endorctl` JSON + Python `create(...)` (template).
8. **Related resources** — same OpenAPI tag or explicit map (e.g. `VectorStore` → `VectorStoreQuery`).

**Do not hand-edit** files under `resources/`; regenerate via `uv run python devtools/model_sync.py --generate-reference-docs`.

### B2. Package index for PyPI consumers

**Where:** `src/endorlabs/generated/README.md` — add table: SDK resource → `resources/<Attr>.md` (GitHub link in repo; path note for clones) → `resources/*.py` module → generated model shard file.

**Optional:** `src/endorlabs/generated/resource_index.json` included in wheel (`pyproject.toml` artifacts) for agents without repo checkout.

### B3. Doc index links

- [docs/README.md](../README.md) — bullet under Generated reference.
- [docs/reference/README.md](../reference/README.md) — link to `generated-reference/resources/README.md`.
- Root [README.md](../../README.md) — one line under reference.

---

## Implementation phases (recommended order)

| Phase | Deliverable | Depends on |
|-------|-------------|------------|
| P0 | This plan + branch | — |
| P1 | A1 — OpenAPI field extraction + `payload_schemas` / registry_contract | — |
| P2 | A2 — `promote_create_kwargs` + unit tests | P1 |
| P3 | A3 pilot — `VectorStoreQuery` + drift/types | P2 |
| P4 | B1 — per-resource `.md` + index (use P1 metadata; convenience list empty until P1) | P1 |
| P5 | A4 — stub `create()` overloads | P1, P3 |
| P6 | A3 rollout — remaining builders | P2, P5 |
| P7 | B2/B3 — README + index.json + doc links | P4 |
| P8 | Contracts + changelog | P3–P7 |

---

## Tests

### Side A — unit

| Test file | Cases |
|-----------|--------|
| `tests/unit/devtools/sync/test_create_convenience_fields.py` | **New.** From fixture OpenAPI fragment: `v1VectorStoreQuerySpec` yields `vector_store_uuid`, `query`, `metadata_filter`; excludes `matches` (readOnly). |
| `tests/unit/utils/test_create_payload_promote.py` | **New.** Promotion moves spec fields; default meta; unknown kwarg raises `TypeError`; `spec=` passthrough unchanged. |
| `tests/unit/resources/test_vector_store_query.py` | **Extend.** `metadata_filter` as flat kwarg appears in `model_dump()["spec"]`; explicit `spec=` still works. |
| `tests/unit/tooling/scripts/test_generated_contract_quality_gates.py` | **Extend.** Registry contract rows include `create_convenience_spec_fields` when create supported. |
| `tests/unit/devtools/test_generate_client_stub.py` | **New or extend.** `_VectorStoreQueryFacade.create` in pyi includes `metadata_filter` param after regen. |

### Side A — integration (optional, credentialed)

| Test file | Cases |
|-----------|--------|
| `tests/integration/resources/test_vector_store_query.py` | **Extend.** If `function_summary` exists: create with `metadata_filter={"repo": ...}` does not error; optionally assert echoed filter on response (skip-friendly). |

### Side B — unit

| Test file | Cases |
|-----------|--------|
| `tests/unit/devtools/test_generate_resource_reference_pages.py` | **New.** Running generator creates `docs/generated-reference/resources/VectorStoreQuery.md` with headings: Create, convenience kwargs, `metadata_filter`, `spec.matches`. |
| `tests/unit/devtools/test_generate_reference_docs.py` | **New or extend.** `resources/README.md` row count == `len(RESOURCE_REGISTRY)` facade entries. |
| Snapshot | Golden file `tests/fixtures/generated-reference/VectorStoreQuery.md` (optional; update on regen). |

### CI / drift

| Gate | Action |
|------|--------|
| `ci-pr-main.yml` | Add check: `docs/generated-reference/resources/*.md` count matches registry; or `git diff --exit-code` after regen. |
| `model_sync.py --generate-reference-docs` | Document in [docs-drift-workflow.md](../rules-of-engagement/docs-drift-workflow.md). |
| Pre-push | Same as existing generated artifact verification. |

---

## Acceptance criteria

- [ ] `client.VectorStoreQuery.create(..., metadata_filter={...})` includes filter in wire payload (unit + optional integration).
- [ ] `client.VectorStoreQuery.create(..., typo_field=1)` raises `TypeError` (unit).
- [ ] Pyright on `client.VectorStoreQuery.create` suggests `vector_store_uuid`, `query`, `metadata_filter` (stub test / manual).
- [ ] `docs/generated-reference/resources/VectorStoreQuery.md` exists and lists convenience kwargs and `spec.matches`.
- [ ] `uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs` is the regen command; CI passes.
- [ ] [contracts.md](../contracts.md) updated for create kwargs policy.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| OpenAPI body uses nested `spec.request` (metadata query) | Skip or special-case in A1; document as not supported for flat kwargs until facade exists. |
| Hand-written payload models omit OpenAPI fields | Drift warnings + generated docs show OpenAPI superset; align hand-written specs incrementally. |
| Large pyi diffs for 41 resources | Acceptable; generated-only; review in PR. |
| Docs not on PyPI wheel | `resource_index.json` in package; README points to GitHub paths for full markdown. |

---

## Commands (implementers)

```bash
git checkout feat/create-convenience-kwargs-and-resource-docs

# After implementation:
uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
uv run python devtools/generate_client_stub.py
uv run ruff check .
uv run pyright
uv run pytest tests/unit/devtools tests/unit/utils/test_create_payload_promote.py tests/unit/resources/test_vector_store_query.py -q
```
