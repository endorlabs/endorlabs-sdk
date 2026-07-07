# Devtools

Contributor setup: [CONTRIBUTORS.md](../CONTRIBUTORS.md).

## Layout

| Module | Role |
| ------ | ---- |
| [`git_staged.py`](git_staged.py) | List staged paths (`git diff --cached`); uses [`endorlabs.utils.repo_paths`](../src/endorlabs/utils/repo_paths.py) |
| [`pre_commit_guards.py`](pre_commit_guards.py) | Pre-commit policy: block `.env` / `.endorlabs-context/`; changelog **Unreleased** reminder |
| [`verify_ship_artifacts.py`](verify_ship_artifacts.py) | Regen + drift; release changelog version gate |
| [`sync_agent_knowledge.py`](sync_agent_knowledge.py) | Authoring → shipped agent bundle |
| [`sync/`](sync/README.md) | Model-sync internals |

Hook wiring only: [`.pre-commit-config.yaml`](../.pre-commit-config.yaml). Policy and consolidation rules: rule [`endor-maintainer-tooling`](../agent-knowledge/rules/endor-maintainer-tooling.md) (repo / `.cursor/rules/` mirror).

For syncing external documentation (OpenAPI spec, user docs), use the programmatic API:

```python
import endorlabs
endorlabs.init(sync_skills="cursor")  # or "claude"/"both" as needed
```

See [AGENTS.md](../AGENTS.md#bootstrap) for agent bootstrap details.

For canonical model-sync internals and maintenance responsibilities, see
[`devtools/sync/README.md`](sync/README.md).
