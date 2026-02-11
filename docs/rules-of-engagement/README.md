# Rules of Engagement

For contributors and AI agents: process and checklists for implementing and validating SDK resources. See [docs/README.md](../README.md) for the full docs index. Resource implementation and troubleshooting are also available as Agent Skills: [.cursor/skills/implement-sdk-resource/](../../.cursor/skills/implement-sdk-resource/), [.cursor/skills/troubleshoot-sdk/](../../.cursor/skills/troubleshoot-sdk/).

- [architecture.md](architecture.md) — Two-layer, registry-driven design; client surface, facade, registry; when adding resources to the Client.
- [resource-implementation.md](resource-implementation.md) — Checklists for adding a new resource; see [conventions.md](../conventions.md).
- [api-validation.md](api-validation.md) — Pre-implementation validation steps; spec path in [conventions.md](../conventions.md).
- [troubleshooting.md](troubleshooting.md) — Workflow only; detailed stories: [docs.endorlabs.com](https://docs.endorlabs.com/) or repo issues.
- [docs-drift-workflow.md](docs-drift-workflow.md) — Unified docs sync and schema drift detection.
- [namespace-traversal.md](namespace-traversal.md) — Traverse and list parameters; patterns and examples.