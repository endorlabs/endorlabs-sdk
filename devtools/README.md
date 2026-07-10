# Devtools

Contributor setup: [CONTRIBUTORS.md](../CONTRIBUTORS.md).

Tracked maintainer automation lives under three buckets. Optional local scratch (probes, benchmarks) stays gitignored under `.endorlabs-context/workspace/` — never commit estate identifiers.

## Layout

| Directory | Role |
| --------- | ---- |
| [`precommit/`](precommit/) | Staged-path helpers and commit guards (`git_staged`, `pre_commit_guards`, `audit_consumer_surfaces`) |
| [`codegen/`](codegen/) | Model-sync, stub/reference generators, agent-knowledge sync, `model_sync_profiles/`, `sync/` |
| [`ship/`](ship/) | Release/CI gates (`verify_ship_artifacts`, `check_vcs_version`, wheel smoke tests) |

GitHub Actions–only helpers (not regen): [`.github/scripts/`](../.github/scripts/README.md).

| Entry | Command |
| ----- | ------- |
| Ship gate | `uv run python devtools/ship/verify_ship_artifacts.py --fetch-spec` |
| Model sync | `uv run python devtools/codegen/model_sync.py --fetch-spec --generate-stubs --generate-reference-docs` |
| Agent knowledge | `uv run python devtools/codegen/sync_agent_knowledge.py` |
| Commit guards | `uv run python devtools/precommit/pre_commit_guards.py <subcommand>` |

Hook wiring only: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml). Policy: rule [`endor-maintainer-tooling`](../agent-knowledge/rules/endor-maintainer-tooling.md).

For syncing external documentation (OpenAPI spec, user docs), use the programmatic API:

```python
import endorlabs
endorlabs.init(sync_skills="cursor")  # or "claude"/"both" as needed
```

See [AGENTS.md](../AGENTS.md#bootstrap) for agent bootstrap details.

Model-sync internals: [`devtools/codegen/sync/README.md`](codegen/sync/README.md).
