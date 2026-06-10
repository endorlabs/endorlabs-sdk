# Changelog

User-facing **Added**, **Changed**, and **Breaking** entries for each release.

**Maintainers:** append to **`## Unreleased`** in the same PR as user-visible changes; use the intake block in [`.github/pull_request_template.md`](../.github/pull_request_template.md). At release, rename Unreleased to `## X.Y.Z` and reset empty subsection headers — [contributing/release-publishing.md](contributing/release-publishing.md). Policy: [agent-knowledge/rules/endor-changelog.md](../agent-knowledge/rules/endor-changelog.md). Do not duplicate breaking-change tables in separate `docs/` files.

## Unreleased

### Added

### Changed

### Breaking

## 0.2.0

First release candidate validated via TestPyPI; consolidates estate workflow unification and release automation gates.

### Added

- **`devtools/verify_ship_artifacts.py`** — canonical CI/release gate: upstream OpenAPI SHA verify, model-sync regen, committed-artifact `git diff`, and agent-knowledge `--verify`.
- **`.github/actions/release-build-gate`** — shared quality + ship-artifact + wheel build for production and TestPyPI releases.
- **`endorlabs.tools.list_sharding`** — `ParentShard`, `parallel_map_shards`, and `list_for_shards` for per-project parallel SDK lists.

### Changed

- **`init(sync_skills="claude")`** — generates repo-root `CLAUDE.md` (bootstrap rules + skill index) and `.claude/commands/` slash commands instead of mirroring `.claude/skills/`.
- **Release and TestPyPI workflows** — full ship-artifact verification before publish; optional `--verify-changelog` on release cuts.
- **CI lint** — uses `verify_ship_artifacts.py` instead of separate upstream-only and non-blocking reference-doc drift steps.
- **Model-sync parity** — `validate_contract_artifacts` fails when registry resources lack canonical OpenAPI mapping.
- **Project-scoped empty lists** — `UserWarning` when `Finding`, `ScanResult`, `PackageVersion`, or `DependencyMetadata` return no rows at the client default namespace without `traverse=True`.
- `sast_rule_manager.py` `--name-filter` uses `meta.name matches` (regex) instead of `contains` for substring rule names.
- **CI Endor security scans** — GitHub Action steps use `enable_pr_comments: true` for platform-managed PR review comments (tenant `PRCommentConfig`). Comprehensive SAST uses `--quick-scan`.

### Breaking

- **Estate workflows** — unified `endor-estate` CLI and workspace layout (replaces removed analytics/compile console scripts). Current usage: [estate/README.md](estate/README.md).

  **Removed console scripts / subcommands**

  | Removed | Replacement |
  |---------|-------------|
  | `endor-analytics-export-deps` | `endor-estate pull` + `endor-estate analyze` |
  | `endor-analytics-risk-cardinality` | `endor-estate analyze` (risk step) |
  | `endor-analytics-risk-family-chart` | `viz/estate_dashboard.html` (risk tab) |
  | `endor-compile-dependency-graph` | `endor-estate analyze` (graph step) |
  | `endor-graph-summarize` | `endor-estate summarize` |
  | `endor-estate plan` | `data/collect_manifest.json` |
  | `endor-estate export` | `endor-estate analyze` (viz step) |

  **Layout**

  | Old | New |
  |-----|-----|
  | `.endorlabs-context/session/<slug>/` | `.endorlabs-context/workspace/<slug>-<YYYYMMDD>/` |
  | `layers/dependency_corpus.jsonl` | `data/dependency_metadata.jsonl` |
  | `layers/findings_sca_vulnerability_main.jsonl` | `data/finding.jsonl` |
  | `layers/publisher_index.jsonl` | `data/package_version.jsonl` |
  | `layers/projects.jsonl` | `data/project.jsonl` |
  | `estate_manifest.json` | `data/collect_manifest.json` |
  | `analyses/*` | `intermediate-representation/*` + `viz/estate_dashboard.html` |

  **Python API**

  - `pull_layers` → `collect_workspace`
  - `session_dir_for` → removed (use `workspace_dir_for`)
  - `load_corpus_records` → `load_dependency_metadata_records`
  - `endorlabs.workflows.estate.session.*` → `endorlabs.workflows.estate.workspace.*`

  **Example**

  Before:

  ```bash
  uv run endor-estate pull --namespace tenant.example.child --layers dependency_corpus,findings_sca_vulnerability_main
  uv run endor-estate analyze risk-cardinality --namespace tenant.example.child
  uv run endor-estate export family-risk-chart --namespace tenant.example.child
  ```

  After:

  ```bash
  uv run endor-estate pull --namespace tenant.example.child
  uv run endor-estate analyze --namespace tenant.example.child --workspace .endorlabs-context/workspace/tenant_example_child-20260608
  ```

  Open `.endorlabs-context/workspace/tenant_example_child-20260608/viz/estate_dashboard.html`.

  **IR artifact renames** — re-run `endor-estate analyze --only graph,viz` after upgrading; old filenames and JSON keys are not read.

  | Old IR file | New IR file |
  |-------------|-------------|
  | `leiden_input.json` | `clustering_graph.json` |
  | `graph_partition.json` | `community_detection.json` |
  | `community_summary.json` | `community_profiles.json` |
  | `publisher_rankings.json` | `producer_rankings.json` |

  | Old schema ID | New schema ID |
  |---------------|---------------|
  | `endor.leiden_input.v1` | `endor.clustering_graph.v1` |
  | `endor.graph_partition.v1` | `endor.community_detection.v1` |
  | `endor.community_summary.v1` | `endor.community_profiles.v1` |
  | `endor.publisher_rankings.v1` | `endor.producer_rankings.v1` |

  Selected compile-graph JSON field renames: `source_id`/`target_id` → `importer_vertex_id`/`producer_vertex_id`; `anchor_package_name` → `linking_package_name`; `consumer_row_count` → `import_evidence_count`; `publishers_with_consumers` → `producers_with_importers`; `inbound_edge_count` → `inbound_import_count`. CLI: `partition_graph` → `detect_communities`; `--partition-*` → `--community-*`.

## 0.1.0

First public pre-release on TestPyPI.

### Added

- **Agent knowledge layout (`agent-knowledge/`)** — authoring root with `rules/` (harness bootstrap), `contracts/` (reference), and `skills/` (task playbooks). Shipped wheel mirrors `agent_knowledge/{rules,contracts,skills}/`.
- **`MANIFEST.json` schema v2** — `rules[]`, `bootstrap.rule_ids`; reference-only `contracts[]`.
- **`agent_knowledge_rule_ids()`** — replaces `agent_bootstrap_contract_ids()`; paths resolve from `rules/`.
- **`rule.schema.json`** — validation for bootstrap rule frontmatter (`id`, `tags`, `summary`).
- **Cursor rule provenance** — generated `.mdc` files include `x-endor-generated`, `x-endor-source`, `x-endor-source-sha256`.
- **Shipped agent bundle** — `src/endorlabs/agent_knowledge/` (skills, contracts, workflow index) materialized to `.endorlabs-context/sdk/` on every `endorlabs.init()`; helpers `agent_knowledge_dir()`, `agent_knowledge_index_path()`, `agent_knowledge_manifest()`.
- **`context.json` init manifest** — written under `.endorlabs-context/` with sdk/platform paths and bootstrap flags.
- **`agent-knowledge/skills/` authorship region** — renamed from `skills-src/`; `schema/` (JSON schemas + authoring guide), `workflows.yaml`, contract frontmatter, and `endorlabs.catalog` skill extension metadata.
- **`devtools/agent_knowledge_catalog.py`** — schema validation, portable `SKILL.md` normalization, workflow catalog merge, pyproject CLI cross-check.
- **`devtools/sync_agent_knowledge.py`** — sync `agent-knowledge/skills/` into the wheel bundle; CI/pre-push `--verify` drift gate (skills, contracts, INDEX, workflows, MANIFEST).
- **Agent bundle integration e2e** — `tests/integration/platform/context/test_agent_knowledge_e2e.py` validates init materialization and retrieve-scan-results workflow against tenant data.

### Breaking

- **Naming coherence** — authoring `agent-knowledge/` (kebab); shipped module `endorlabs.agent_knowledge` (snake); sync `devtools/sync_agent_knowledge.py`. Public API: `agent_knowledge_dir()`, `agent_knowledge_manifest()`, `agent_knowledge_rule_ids()`, `agent_knowledge_bootstrap_paths()`; `InitStatus.agent_knowledge_path`; `init(include_agent_knowledge=...)`. Removed `agent_bundle_*` / `include_sdk_bundle` names (no shims).
- **Authoring root** — `agent-skills/` → `agent-knowledge/`; skill directories under `agent-knowledge/skills/`.
- **Bootstrap content** — moved from `contracts/` to `rules/` in authoring and shipped bundle.
- **Manifest** — `schema_version` 2; `bootstrap.contract_ids` → `bootstrap.rule_ids`; bootstrap rows removed from `contracts[]`.
- **Public API** — `agent_bootstrap_contract_ids()` removed; use `agent_knowledge_rule_ids()`.

### Changed

- **Model-sync pipeline** — in-memory staging (dicts + in-process `datamodel_code_generator`); removed committed `workspace/model-sync/` tree; disk writes limited to ship surface (`src/endorlabs/generated/`, stub, reference docs). Path safety via `find_repo_root()` + `safe_repo_output_path()`; removed `--output-root` and `--spec-path` from maintainer CLI.
- **Model-sync maintainer tooling** — removed git-baseline PR delta helpers (`model_sync_pr_deltas.py`, `--delta-summary`); SHA verify (`--verify-upstream-only`), deterministic regen, and CI/pre-push drift gates unchanged.
- **`.endorlabs-context/` layout** — `platform/openapi/`, `platform/user-docs/`, `sdk/`, `workspace/` (flat root OpenAPI/docs paths are not supported).
- **`InitStatus`** — adds `agent_knowledge_path`, `context_json_path`, `platform_*` fields; `openapi_path` / `user_docs_path` remain as aliases.
- **`sync_skills`** — mirrors from materialized `sdk/skills/`, not repo `agent-knowledge/skills/` (pip-safe).
- **Workflow default outputs** — project artifacts under `.endorlabs-context/workspace/projects/`; troubleshooting session root under `workspace/sessions/troubleshooting/`.
- **Skills and docs paths** — canonical local OpenAPI/user-docs paths under `.endorlabs-context/platform/`; shipped bundle INDEX documents SDK-only vs bootstrap modes.
- **Shipped `SKILL.md` frontmatter** — portable subset only (`name`, `description`, optional `disable-model-invocation`); `endorlabs.catalog` stripped at sync.
