# Analytics workflows

Non-normative guides for estate-scale dependency analytics in the SDK. These workflows
are **operator/maintainer tools** — listed in the shipped workflow catalog
(`MANIFEST.json` → `workflows`) but not exposed as agent skills.

## Guides

| Guide | CLI | Question it answers |
|-------|-----|---------------------|
| [compile-dependency-graph.md](compile-dependency-graph.md) | `endor-compile-dependency-graph` | Estate-wide **compile** import topology: hubs, isolation, communities, DM corpus |
| [endor-analytics-estate-dependencies](../../agent-knowledge/skills/endor-analytics-estate-dependencies/SKILL.md) | `endor-analytics-export-deps` | Version cardinality and CVE remediation aggregates across an estate |
| [relationships map](../../src/endorlabs/workflows/relationships/map.py) | `python -m endorlabs.workflows.relationships.map` | Namespace project graph with **transitive** paths |

## Choosing a workflow

| Need | Use |
|------|-----|
| One repository context bundle | `endor-agent-context` — [endor-project-agent-context](../../agent-knowledge/skills/endor-project-agent-context/SKILL.md) |
| Cross-project edges in one namespace (direct + indirect) | `relationships.map` |
| How many versions of package X estate-wide? | `endor-analytics-export-deps` |
| Internal publisher hubs, compile communities, package-XYZ corpus | [compile-dependency-graph.md](compile-dependency-graph.md) |

Implementation detail for compile-graph phases lives in
[`src/endorlabs/workflows/relationships/README.md`](../../src/endorlabs/workflows/relationships/README.md).
