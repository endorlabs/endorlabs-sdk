# Rules of Engagement

For contributors and AI agents: process and checklists for extending and validating the generated SDK client surface. See [docs/README.md](../README.md) for the full docs index. Agent skills: [.cursor/skills/implement-sdk-resource/](../../.cursor/skills/implement-sdk-resource/), [.cursor/skills/troubleshoot-sdk/](../../.cursor/skills/troubleshoot-sdk/).

- [architecture.md](architecture.md) — Layers, registry, facade; contributing after model sync (overlay, `resources/` deltas).
- [integration-resource-tests.md](integration-resource-tests.md) — Integration test order, pagination profiles (generic vs log); see [contracts.md](../contracts.md).
- [api-validation.md](api-validation.md) — Pre-implementation validation steps; spec path in [contracts.md](../contracts.md).
- [troubleshooting.md](troubleshooting.md) — Workflow only; detailed stories: local docs snapshots or repo issues.
- [docs-drift-workflow.md](docs-drift-workflow.md) — Unified docs sync and canonical model sync workflow.
- [namespace-traversal.md](namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [list-query-performance.md](list-query-performance.md) — Scope, filters, pagination, and debugging slow list calls.
