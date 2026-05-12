# Agent Skills

Modular, on-demand workflow packages for AI agents working with the Endor Labs SDK. Each skill is a directory containing a `SKILL.md` (condensed workflow) and optional reference files (loaded only when needed).

These skills follow the cross-compatible format supported by both [Cursor](https://docs.cursor.com) and [Anthropic Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).

## Available Skills

| Skill | Trigger | Source docs |
|-------|---------|-------------|
| [project-agent-context](project-agent-context/) | Multi-pass bundle: PV index + hydration + optional sweep; `context_manifest.json`; deep LLM contract in [MULTIPASS_LLM_CONTRACT.md](project-agent-context/MULTIPASS_LLM_CONTRACT.md) | `endorlabs.workflows.agent_context` |
| [custom-sast-rules](custom-sast-rules/) | Threat modeling, authoring, or importing OpenGrep/Semgrep rules | Canonical (skill-owned) |
| [dependency-provenance](dependency-provenance/) | Resolve exact package lineage by manifest path/ref and direct-vs-transitive introduction routes | Skill-owned |
| [dependency-finding-provenance](dependency-finding-provenance/) | Trace vulnerability/dependency lineage and commit-scoped presence across findings, package versions, and artifacts | Skill-owned |
| [fetch-and-search-call-graph](fetch-and-search-call-graph/) | Fetch/decode call graphs and run safe node/edge/path retrieval workflows | `endorlabs.workflows.callgraph` |
| [implement-sdk-resource](implement-sdk-resource/) | Adding a new Endor Labs resource to the SDK | `docs/rules-of-engagement/` |
| [retrieve-scan-results](retrieve-scan-results/) | Querying findings, scan results, or projects | `docs/guides/`, `docs/rules-of-engagement/` |
| [map-project-dependency-relationships](map-project-dependency-relationships/) | Namespace-wide project dependency relationship graphing (direct + indirect) with JSON outputs | Skill-owned |
| [troubleshooting-scans](troubleshooting-scans/) | Scan regressions; anomalous ScanResults, ScanLogs, scripted diffs | `endorlabs.workflows.troubleshooting_scans`; see `docs/guides/`, `docs/rules-of-engagement/list-query-performance.md` |
| [troubleshoot-sdk](troubleshoot-sdk/) | Debugging SDK errors, 404s, 500s, or test failures | `docs/rules-of-engagement/` |
| [troubleshoot-authlog](troubleshoot-authlog/) | AuthenticationLog / AuthorizationPolicy / SSO login troubleshooting | Skill-owned |

## How Loading Works

Skills use progressive disclosure to minimize context window usage:

1. **Metadata (always loaded)**: The `name` and `description` from YAML frontmatter are included in the system prompt so the agent knows each skill exists.
2. **Instructions (on trigger)**: When a task matches a skill's description, the agent reads `SKILL.md` into context.
3. **Reference files (as needed)**: Detailed guides, syntax cards, and checklists are read only when the agent needs them.

## Location

**Source of truth:** this directory, `skills-src/`, is mirrored into [`.cursor/skills/`](../.cursor/skills/) for Cursor discovery. Edit here first, then sync the same skill tree to `.cursor/skills/` (see [AGENTS.md](../AGENTS.md) — agent skills table).

To refresh runtime mirrors from the repo root:

```bash
uv run endor-context --no-openapi --no-user-docs --sync-skills auto
```

For **Claude Code** users: copy either `skills-src/` or `.cursor/skills/` to `.claude/skills/` at the repo root. The SKILL.md format is identical.

For **Claude API** users: zip each skill directory and upload via the `/v1/skills` endpoints. See [Anthropic Skills API docs](https://platform.claude.com/docs/en/build-with-claude/skills-guide).

## Relationship to Other Docs

- **`docs/`**: Full reference material. Skills condense and link to these; originals are unchanged.
- **`.cursor/rules/`**: Always-on project rules (apply every session). Skills are on-demand (apply when triggered).
- **`AGENTS.md`**: Project index for AI agents. Points here for skill discovery.

## Security

Only use skills from trusted sources. Skills provide agents with instructions and may reference executable scripts. Review all files before use. See [Anthropic's security guidance](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#security-considerations).
