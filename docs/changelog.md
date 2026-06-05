# Changelog

## Unreleased

### Added

- **Shipped agent bundle** — `src/endorlabs/agent_bundle/` (skills, contracts, workflow index) materialized to `.endorlabs-context/sdk/` on every `endorlabs.init()`; helpers `agent_bundle_dir()`, `agent_index_path()`, `agent_manifest()`.
- **`context.json` init manifest** — written under `.endorlabs-context/` with sdk/platform paths and bootstrap flags.
- **`agent-skills/` authorship region** — renamed from `skills-src/`; `schema/` (JSON schemas + authoring guide), `workflows.yaml`, contract frontmatter, and `endorlabs.catalog` skill extension metadata.
- **`devtools/agent_bundle_catalog.py`** — schema validation, portable `SKILL.md` normalization, workflow catalog merge, pyproject CLI cross-check.
- **`devtools/sync_agent_bundle.py`** — sync `agent-skills/` into the wheel bundle; CI/pre-push `--verify` drift gate (skills, contracts, INDEX, workflows, MANIFEST).
- **Agent bundle integration e2e** — `tests/integration/platform/context/test_agent_bundle_e2e.py` validates init materialization and retrieve-scan-results workflow against tenant data.

### Changed

- **Model-sync pipeline** — in-memory staging (dicts + in-process `datamodel_code_generator`); removed committed `workspace/model-sync/` tree; disk writes limited to ship surface (`src/endorlabs/generated/`, stub, reference docs). Path safety via `find_repo_root()` + `safe_repo_output_path()`; removed `--output-root` and `--spec-path` from maintainer CLI.
- **Model-sync maintainer tooling** — removed git-baseline PR delta helpers (`model_sync_pr_deltas.py`, `--delta-summary`); SHA verify (`--verify-upstream-only`), deterministic regen, and CI/pre-push drift gates unchanged.
- **`.endorlabs-context/` layout** — `platform/openapi/`, `platform/user-docs/`, `sdk/`, `workspace/` (flat root OpenAPI/docs paths are not supported).
- **`InitStatus`** — adds `agent_bundle_path`, `context_json_path`, `platform_*` fields; `openapi_path` / `user_docs_path` remain as aliases.
- **`sync_skills`** — mirrors from materialized `sdk/skills/`, not repo `agent-skills/` (pip-safe).
- **Workflow default outputs** — project artifacts under `.endorlabs-context/workspace/projects/`; troubleshooting session root under `workspace/sessions/troubleshooting/`.
- **Skills and docs paths** — canonical local OpenAPI/user-docs paths under `.endorlabs-context/platform/`; shipped bundle INDEX documents SDK-only vs bootstrap modes.
- **Shipped `SKILL.md` frontmatter** — portable subset only (`name`, `description`, optional `disable-model-invocation`); `endorlabs.catalog` stripped at sync.
