# API Surfaces

Consumer-facing SDK entry points and where to find canonical inventories.

## When to use which surface

| Surface                                 | When                                                                                                                                                        |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `endorlabs.Client`                      | Default typed API access                                                                                                                                    |
| `endorlabs.APIClient`                   | Raw HTTP transport                                                                                                                                          |
| `endorlabs.init()` / `endor-context`    | Materialize agent knowledge; opt-in OpenAPI/user-docs — see [AGENTS.md](../../AGENTS.md)                                                                     |
| `endorlabs.workflows` + console scripts | Tenant workflows — inventory in shipped `MANIFEST.json` (`workflows`, `workflows/entries.json`) and `[project.scripts]` in [pyproject.toml](../../pyproject.toml) |

Agent knowledge naming: authoring `agent-knowledge/` → shipped `src/endorlabs/agent_knowledge/` → runtime `.endorlabs-context/sdk/`. Details: [AGENTS.md — Agent knowledge naming](../../AGENTS.md#agent-knowledge-naming) · [repository-layout.md](../contributing/repository-layout.md).

## Custom facades

- **`CallGraphData`** — decode/fetch call graph payloads by parent `PackageVersion`; not yet a full registry list/get surface.
- **`ScanResult.get_logs`** — log lines via ScanLogRequest wire API (not a separate client attr).
- See [facade-helpers.md](../guides/facade-helpers.md) and [contracts.md](../contracts.md).

## Generated reference

- Canonical generated API surface inventory: [../generated-reference/api-surfaces.md](../generated-reference/api-surfaces.md)
- Resource matrix: [../generated-reference/resources.md](../generated-reference/resources.md)
- Reference index and ownership policy: [README.md](README.md)
