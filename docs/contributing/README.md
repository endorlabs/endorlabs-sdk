# Contributing to the SDK

Process and checklists for contributors and AI agents extending the **generated** client surface. Setup and commands: [CONTRIBUTORS.md](../../CONTRIBUTORS.md). Full docs index: [docs/README.md](../README.md).

Agent skills: [endor-implement-sdk-resource](../../agent-knowledge/skills/endor-implement-sdk-resource/), [endor-model-sync-drift](../../agent-knowledge/skills/endor-model-sync-drift/), [endor-troubleshoot-sdk](../../agent-knowledge/skills/endor-troubleshoot-sdk/).

- [repository-layout.md](repository-layout.md) — Tracked vs gitignored regions, `.endorlabs-context/`, workflows vs skills.
- [architecture.md](architecture.md) — Layers, registry, facade; regen, overlay, `resources/` deltas.
- [release-publishing.md](release-publishing.md) — Version tags, hatch-vcs, OIDC PyPI/TestPyPI release CI.
- [pr-review-comments.md](pr-review-comments.md) — Endor findings → GitHub PR review comments in CI.
- [pr-review-comment-matrix.md](pr-review-comment-matrix.md) — Finding fields vs GitHub review comment payloads.
- PR template: [`.github/pull_request_template.md`](../../.github/pull_request_template.md) — changelog intake block; policy in [agent-knowledge/rules/endor-changelog.md](../../agent-knowledge/rules/endor-changelog.md).
- [integration-resource-tests.md](integration-resource-tests.md) — Integration test order, pagination profiles (generic vs log); see [contracts.md](../contracts.md).
- [api-validation.md](api-validation.md) — OpenAPI and optional wire validation before overlay or hand modules.
- [troubleshooting.md](troubleshooting.md) — SDK failure workflows; detailed stories in local docs or issues.
- [docs-drift-workflow.md](docs-drift-workflow.md) — Model sync and reference doc regeneration.
- [namespace-traversal.md](namespace-traversal.md) — Traverse and list parameters; patterns and examples.
- [list-query-performance.md](list-query-performance.md) — Scope, filters, pagination, debugging slow lists.
