---
name: endor-model-sync-drift
description: >-
  Triage and fix OpenAPI / model-sync upstream drift when CI or pre-push fails
  verify-upstream-only, or when published endorctl is newer than committed
  provenance. Use for regenerating registry_contract, stubs, and reference docs;
  reviewing generated diffs; and optional local endorctl upgrades. Not for
  runtime SDK API errors (see troubleshoot-sdk).
---

# Model-sync upstream drift

When **OpenAPI SHA-256** in live upstream differs from `src/endorlabs/generated/registry_contract.py` provenance, CI and pre-push **fail**. Pre-commit runs local regen + ship `git diff` (no upstream fetch) before linters when generated paths change. A newer **published endorctl** alone is a **warning** only until you re-run model sync.

## Quick diagnose

```bash
uv run python devtools/model_sync.py --verify-upstream-only
```

Exit `0` = committed artifacts match upstream. Non-zero = regen required (message includes committed vs upstream digests).

Optional: compare published CLI version (no auth):

```bash
uv run python .github/scripts/check_endorctl_version.py
```

## Regenerate (canonical)

From repo root (public spec download):

```bash
uv run python devtools/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs
```

**Spec already in `.endorlabs-context/platform/openapi/openapiv2.swagger.json`:**

```bash
uv run python devtools/model_sync.py --generate-stubs --generate-reference-docs
```

**Refresh only if verify failed:**

```bash
uv run python devtools/model_sync.py --verify-and-sync-if-stale
```

Provenance watermark (`endorctl_version`, `spec_sha256`) comes from **`GET /meta/version`** and the downloaded OpenAPI file during generation—not from a stale local `endorctl` binary.

## Review checklist before push

| Area | What to scan |
|------|----------------|
| `src/endorlabs/generated/` | `registry_contract.py`, `models/`, `create_convenience.py`, provenance headers |
| `src/endorlabs/client_surface.pyi` | Stub drift after registry/facade changes |
| `docs/generated-reference/` | Per-resource pages if generator touched resources |
| Overlays | `src/endorlabs/registry_overlay.py`, `devtools/model_sync_profiles/` only if API introduced new resources or scope fixes |

Run locally before push:

```bash
uv run ruff check .
uv run pyright --project pyproject.toml
uv run pytest
```

Pre-commit runs `verify_ship_artifacts.py --skip-upstream` before ruff/pyright on
model-sync changes. Pre-push runs `verify_ship_artifacts.py --fetch-spec` (upstream SHA +
agent-knowledge verify) and contract validation.

## When this is not enough

- **New resource or facade behavior** → [endor-implement-sdk-resource](../endor-implement-sdk-resource/SKILL.md) and [docs/contributing/architecture.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/architecture.md).
- **Runtime list/get/update failures** → [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md).
- **Contract/list validation on masked rows** → [docs/guides/consumer-ux-list-update.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/guides/consumer-ux-list-update.md).

## Local endorctl upgrade (optional, for parity with UI/endorctl)

SDK model-sync does **not** require a matching local `endorctl` for regen. To upgrade the CLI for manual `endorctl api` checks: `npm update -g endorctl` then `endorctl --version`, or follow [Endor CLI install](https://docs.endorlabs.com/developers-api/cli/install-and-configure/) (stop processes locking `endorctl.exe` on Windows before replacing the binary).

## References

- [docs/contributing/docs-drift-workflow.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/docs-drift-workflow.md)
- [devtools/sync/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/devtools/sync/README.md)
- [docs/contributing/docs-drift-workflow.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/contributing/docs-drift-workflow.md) — Model-sync drift enforcement
