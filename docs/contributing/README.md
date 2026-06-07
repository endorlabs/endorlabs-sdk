# Contributing to the SDK

Process and checklists for contributors and AI agents extending the **generated** client surface. Setup and commands: [CONTRIBUTORS.md](../../CONTRIBUTORS.md). Full docs index: [docs/README.md](../README.md).

Agent skills: [endor-implement-sdk-resource](../../agent-knowledge/skills/endor-implement-sdk-resource/), [endor-model-sync-drift](../../agent-knowledge/skills/endor-model-sync-drift/), [endor-troubleshoot-sdk](../../agent-knowledge/skills/endor-troubleshoot-sdk/).

- [architecture.md](architecture.md) — Layers, registry, facade; regen, overlay, `resources/` deltas.
- [integration-resource-tests.md](integration-resource-tests.md) — Integration test order, pagination profiles (generic vs log); see [contracts.md](../contracts.md).
- [api-validation.md](api-validation.md) — OpenAPI and optional wire validation before overlay or hand modules.
- [troubleshooting.md](troubleshooting.md) — SDK failure workflows; detailed stories in local docs or issues.
- [docs-drift-workflow.md](docs-drift-workflow.md) — Model sync and reference doc regeneration.
- [namespace-traversal.md](namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [list-query-performance.md](list-query-performance.md) — Scope, filters, pagination, debugging slow lists.
