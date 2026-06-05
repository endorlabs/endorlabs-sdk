# Changelog

## Unreleased

### Added

- **Agent knowledge layout (`agent-knowledge/`)** — authoring root with `rules/` (harness bootstrap), `contracts/` (reference), and `skills/` (task playbooks). Shipped wheel mirrors `agent_knowledge/{rules,contracts,skills}/`.
- **`MANIFEST.json` schema v2** — `rules[]`, `bootstrap.rule_ids`; reference-only `contracts[]`.
- **`agent_knowledge_rule_ids()`** — replaces `agent_bootstrap_contract_ids()`; paths resolve from `rules/`.
- **`rule.schema.json`** — validation for bootstrap rule frontmatter (`id`, `tags`, `summary`).
- **Cursor rule provenance** — generated `.mdc` files include `x-endor-generated`, `x-endor-source`, `x-endor-source-sha256`.

### Breaking

- **Naming coherence** — authoring `agent-knowledge/` (kebab); shipped module `endorlabs.agent_knowledge` (snake); sync `devtools/sync_agent_knowledge.py`. Public API: `agent_knowledge_dir()`, `agent_knowledge_manifest()`, `agent_knowledge_rule_ids()`, `agent_knowledge_bootstrap_paths()`; `InitStatus.agent_knowledge_path`; `init(include_agent_knowledge=...)`. Removed `agent_bundle_*` / `include_sdk_bundle` names (no shims).
- **Authoring root** — `agent-skills/` → `agent-knowledge/`; skill directories under `agent-knowledge/skills/`.
- **Bootstrap content** — moved from `contracts/` to `rules/` in authoring and shipped bundle.
- **Manifest** — `schema_version` 2; `bootstrap.contract_ids` → `bootstrap.rule_ids`; bootstrap rows removed from `contracts[]`.
- **Public API** — `agent_bootstrap_contract_ids()` removed; use `agent_knowledge_rule_ids()`.

### Added

- **Shipped agent bundle** — `src/endorlabs/agent_knowledge/` (skills, contracts, workflow index) materialized to `.endorlabs-context/sdk/` on every `endorlabs.init()`; helpers `agent_knowledge_dir()`, `agent_knowledge_index_path()`, `agent_knowledge_manifest()`.
- **`context.json` init manifest** — written under `.endorlabs-context/` with sdk/platform paths and bootstrap flags.
- **`agent-knowledge/skills/` authorship region** — renamed from `skills-src/`; `schema/` (JSON schemas + authoring guide), `workflows.yaml`, contract frontmatter, and `endorlabs.catalog` skill extension metadata.
- **`devtools/agent_knowledge_catalog.py`** — schema validation, portable `SKILL.md` normalization, workflow catalog merge, pyproject CLI cross-check.
- **`devtools/sync_agent_knowledge.py`** — sync `agent-knowledge/skills/` into the wheel bundle; CI/pre-push `--verify` drift gate (skills, contracts, INDEX, workflows, MANIFEST).
- **Agent bundle integration e2e** — `tests/integration/platform/context/test_agent_knowledge_e2e.py` validates init materialization and retrieve-scan-results workflow against tenant data.

### Changed

- **Model-sync pipeline** — in-memory staging (dicts + in-process `datamodel_code_generator`); removed committed `workspace/model-sync/` tree; disk writes limited to ship surface (`src/endorlabs/generated/`, stub, reference docs). Path safety via `find_repo_root()` + `safe_repo_output_path()`; removed `--output-root` and `--spec-path` from maintainer CLI.
- **Model-sync maintainer tooling** — removed git-baseline PR delta helpers (`model_sync_pr_deltas.py`, `--delta-summary`); SHA verify (`--verify-upstream-only`), deterministic regen, and CI/pre-push drift gates unchanged.
- **`.endorlabs-context/` layout** — `platform/openapi/`, `platform/user-docs/`, `sdk/`, `workspace/` (flat root OpenAPI/docs paths are not supported).
- **`InitStatus`** — adds `agent_knowledge_path`, `context_json_path`, `platform_*` fields; `openapi_path` / `user_docs_path` remain as aliases.
- **`sync_skills`** — mirrors from materialized `sdk/skills/`, not repo `agent-knowledge/skills/` (pip-safe).
- **Workflow default outputs** — project artifacts under `.endorlabs-context/workspace/projects/`; troubleshooting session root under `workspace/sessions/troubleshooting/`.
- **Skills and docs paths** — canonical local OpenAPI/user-docs paths under `.endorlabs-context/platform/`; shipped bundle INDEX documents SDK-only vs bootstrap modes.
- **Shipped `SKILL.md` frontmatter** — portable subset only (`name`, `description`, optional `disable-model-invocation`); `endorlabs.catalog` stripped at sync.
