# Changelog

User-facing **Added**, **Changed**, and **Breaking** entries for each release.

**Maintainers:** append to **`## Unreleased`** in the same PR as user-visible changes; use the intake block in [`.github/pull_request_template.md`](../.github/pull_request_template.md). At release, rename Unreleased to `## X.Y.Z` and reset empty subsection headers — [contributing/release-publishing.md](contributing/release-publishing.md). Policy: [agent-knowledge/rules/endor-changelog.md](../agent-knowledge/rules/endor-changelog.md). Do not duplicate breaking-change tables in separate `docs/` files.

## Unreleased

### Added

- **`endorlabs.discover()`** — programmatic wheel paths for agent onboarding (INDEX, bootstrap, stub, `agent_bootstrap` module, entry points).
- **Wheel `AGENTS.md`** and **`python -m endorlabs.examples.agent_bootstrap`** — consumer agent guide and bounded smoke-test ladder (`--dry-run` for path-only checks).
- **Bootstrap contracts** — `resource-discovery`, `errors-and-auth`, and `list-parameters` included in `agent_knowledge_bootstrap_paths()`.

### Changed

- **`SdkDiscovery.__str__`** — `print(discover())` and `agent_bootstrap --dry-run` emit a human-readable path map (relative bootstrap labels, `endor-*` entry points only); agent INDEX/AGENTS frontmatter documents the three-step ladder (map → auth → workflows).
- Renamed **`endorlabs.examples.day0`** → **`endorlabs.examples.agent_bootstrap`**; `SdkDiscovery.day0_module` → **`agent_bootstrap_module`**.
- **`RouteResult`** — relationship accessors (`list_by_*`, …) are iterable; use `for row in result` or `.values` / `.value` (plain `.list()` still returns `list`).
- **`endorlabs` module docstring** — quickstart for `discover()`, `F("path")` filters, and `RouteResult` iteration (visible via `help(endorlabs)`).
- API and validation exceptions now include gRPC remediation hints, payload field paths, namespace-scoping guidance on 404s, structured error details in `str(exc)`, and `NetworkError` for exhausted transport retries.
- **`client_surface.pyi`** — flat `search_by_*`, `list_by_*`, `get_logs`, and related methods on `_XFacade` classes for agent Read discovery without LSP inheritance.
- **Auth** — missing-credential `ValidationError` documents `ENDOR_TOKEN`; INFO log when token and API key env vars are both set (token path preferred; MCP/endorctl need single mode).
- **`Client.__init__`** — runtime docstring for `help()` / inspect.
- Top-level **`__all__`** — removed `query_vulnerability` and `query_malware` (use `client.QueryVulnerability` / `client.QueryMalware`).

### Breaking

## 0.4.0

Call-graph export/path workflows, vector-store query CLI, and sweep→export breaking rename. Generated models pinned to **endorctl `v1.7.1002`** (OpenAPI spec SHA-256 `663e91e0…33556`).

### Added

- **Call-graph export primitives** — `run_callgraph_export`, `find_call_graph_path`, `resolve_package_version_with_callgraph`, and `resolve_callgraph_export_artifact` under `endorlabs.workflows.callgraph`.
- **CLIs** — `endor-callgraph-path` (live project path search); `endor-callgraph-search` path mode (`--path-from`, `--path-to`, `--max-depth`); `endor-vector-query` (list/probe/query tenant vector stores).

### Changed

- **Pass 3 naming** — `endor-agent-context` uses `--callgraph-export`, output subdir `callgraph_export/`, and manifest key `artifacts.callgraph_export`.
- **Call-graph search** — multi-hop BFS is a first-class library/CLI primitive; skills updated accordingly.

### Breaking

- Removed **`--callgraph-sweep`** CLI flag — use **`--callgraph-export`**.
- Removed **`run_callgraph_sweep`** and **`endorlabs.workflows.callgraph.sweep`** — use **`run_callgraph_export`**.
- Removed **`artifacts.callgraph_sweep`**, **`callgraph_sweep/`**, and **`callgraph_sweep_manifest.json`** — use **`artifacts.callgraph_export`**, **`callgraph_export/`**, and **`callgraph_export_manifest.json`**.

## 0.3.0

V1 consumer facade cutover: package split, contract-driven routes, `search_by_*` discovery, generated relationship accessors, and removal of deprecated lookup/resolve/shim surfaces. See **Breaking** below for migration paths.

### Added

- **Scan-plane partition accessors** — `{Kind}.list_for_context(source)` and `context_partition_filter()` list rows sharing `context.type` + `context.id` with a source row (e.g. `ScanResult`). See [facade-helpers.md](guides/facade-helpers.md) and [resource-routes.md](generated-reference/resource-routes.md).
- **Generated accessor helpers** — `Finding.list_by_project`, `Finding.to_dependency_metadata`, `ScanResult.list_by_project`, `PackageVersion.list_by_project` return `RouteResult`; relationship map in [resource-routes.md](generated-reference/resource-routes.md). Regenerate with `devtools/generate_route_contract.py`.
- **Identity lane** — `Project.search_by_name`, `VectorStore.search_by_name`, `AuthorizationPolicy.search_by_claims`, `Vulnerability.search_by_vuln_alias` (bounded list discovery; forwards `list()` kwargs including `mask` and `filter` / `F()`). Contract: [resource-discovery.md](../agent-knowledge/contracts/resource-discovery.md).
- **Facade package** — `facade/` split (`base`, `runtime`, `route_host`, `specialized`, `search`) replacing monolithic `facade.py`.
- **Facade list helpers** — `count()`, `list_groups()`, `latest()` / `latest_created()` / `latest_updated()`, `parent()` on listable facades; catalog in [facade-helpers.md](guides/facade-helpers.md).
- **Facade sugar** — `CallGraphData.decode()` / `fetch()`, `ScanResult.get_logs()`, `ScanResult.latest_created(parent=…)`.

### Changed

- **Discovery** — use `search_by_*` + explicit disambiguation or `get(uuid)` instead of `lookup()` / `Project.resolve()`. See [facade-helpers.md](guides/facade-helpers.md) and `resource-discovery` contract.
- Troubleshooting scan workflows use `ScanResult.list_by_project` and `Project.search_by_name` instead of hand-built filters / `workflows.projects.resolve`.
- Architecture doc: consumer vs generated model planes ([architecture.md](contributing/architecture.md)); removed per-resource schema drift validators; `PolicySpec.finding` / `.notification` use typed config models.
- Estate grouped counts and collect preflight use `facade.count()` / `DependencyMetadata.list_groups()` instead of workflow-local pagination helpers.
- Troubleshooting scan workflows and dependency metadata fetch use `Client` facades instead of raw `APIClient.get` / `get_all` loops.
- CallGraphData wire/decode moved from `operations/call_graph.py` to `resources/call_graph_data.py`; protobuf decoder to `resources/call_graph_data_proto.py`.

### Breaking

- Removed **`Finding.list_by_scan`** — use **`Finding.list_for_context(scan)`** or `list_by_project` + `context_partition_filter(scan.context)`; no shim.
- Removed **`ListableFacade.lookup()`** — use `search_by_*` (discovery) or `get(uuid)`; no shim.
- Removed **`Project.resolve()`** — use `Project.search_by_name`, `get(uuid)`, or `workflows.projects.discovery.resolve_project_candidate`.
- Removed **`workflows.projects.resolve`** (`search_projects_by_name_or_uuid`) — use `client.Project.search_by_name`.
- Removed **`Finding.to_semgrep_rule`** — no workflow or skill consumer; use explicit `Finding.list` / `SemgrepRule.get` when needed.
- Removed **`Finding.list_for_scan`** and **`ScanResult.list_for_project`** — use **`list_for_context`** / **`list_by_project`** (`RouteResult`).
- Removed **`list_scan_results_for_project`** and **`list_projects`** from `workflows.troubleshooting_scans` — use `client.ScanResult.list_by_project` and `client.Project.search_by_name`.
- Removed **`operations.call_graph`** — use **`resources.call_graph_data`** and `client.CallGraphData.decode` / `fetch`.
- Removed **`workflows.callgraph.proto_decode`** — use **`resources.call_graph_data_proto`**.
- **`retrieve_dep_metadata_full`** now takes **`endorlabs.Client`** (first argument), not `APIClient`.
- **`process_project`** (agent context hydration) no longer accepts `api_client`.
- **`run_callgraph_sweep`** no longer accepts `_api_client`.
- Removed **`endorlabs.utils.api_pagination`** (`paginate_raw`, `extract_objects`) — use `facade.list()` / `api_client.get_all` or `operations.list_response.extract_list_objects`.
- Removed **`list_resource_count`** from `workflows.estate.collect.bounds` — use `facade.count()` or `count_for_progress`.
- Removed **`retrieve_call_graph_full`** / **`retrieve_call_graph_for_client`** from `workflows.callgraph.fetch` — use `client.CallGraphData.decode` / `fetch`.
- Removed **`client.ScanLogs`** — use `client.ScanResult.get_logs`.
- Removed **`workflows.estate.collect.shards`** — use **`endorlabs.tools.list_sharding`**.
- Removed **`endorlabs.utils.tabular`** re-exports — use **`workflows.estate.analyze.cardinality.tabular`**.
- Removed **`workflows.projects.resolve.resolve_project`** and **`troubleshooting_scans.resolve_project`** re-export — use **`client.Project.search_by_name`** ([facade-helpers.md](guides/facade-helpers.md)).
- Removed **`endorlabs.tools.dependency_explorer`** — use `workflows.agent_context.hydration`, `workflows.dependencies.*`, `workflows.callgraph.*`, and `client.CallGraphData`.
- Removed **`endorlabs.models`** — use **`endorlabs.resources.base`** (and `resources.finding_config`, `resources.notification_config`, `resources.exception_config`, `resources.field_aliases`).
- Removed **`SchemaDriftDetector`** from **`endorlabs.utils`** — opt-in wire probes: `endorlabs.utils.schema_drift.log_unknown_wire_keys` (not in `__all__`).

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
