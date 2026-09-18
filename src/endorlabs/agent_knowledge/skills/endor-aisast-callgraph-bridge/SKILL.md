---
name: endor-aisast-callgraph-bridge
description: 'Use when mapping AI-SAST function_summary vector seeds (entry points
  / rest_path metadata) onto customer PackageVersion CallGraphData symbols, with hard
  prechecks that MAIN RepositoryVersion AI-SAST SUCCESS and a function_summary index
  exist plus a MAIN-context call-graph PackageVersion is decodable. Optional safe
  BFS via --path-to and/or Finding-derived package tokens (--vuln / --finding-package).
  Not for Finding/oss SCA reachability proof (endor-reachability-provenance), offline
  CG-only search (endor-fetch-and-search-call-graph), or NL-only vector browse (endor-vector-query).

  '
---

# AI-SAST → Call Graph bridge

Join **AI-SAST `function_summary`** seeds (smaller, labeled first-party set) as
**inputs** to query **SCA CallGraphData** (larger structural graph). Hard-fail
when either plane is missing. Only **`CONTEXT_TYPE_MAIN` RepositoryVersions**
count for AI-SAST readiness.

## Scope

**In scope**

- Prechecks: MAIN RV `aisast_status` SUCCESS; `function_summary` indexed for
  `repo=<project.meta.name>`; MAIN PackageVersion with decodable CallGraphData
- Seed query → CG URI pattern match (`file_path` / `fqn` fragments — never
  treat `rest_path` as a CG URI)
- Optional **safe** multi-hop BFS when `--path-to` and/or `--vuln` /
  `--finding-package` is set (depth/path/fanout caps; advisory ids never
  used as CG URI patterns)

**Out of scope**

- Finding / `oss` function reachability **proof** → [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md)
  (CG path ≠ `FINDING_TAGS_REACHABLE_FUNCTION`)
- Offline decoded JSON search only → [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md)
- CI/REF RepositoryVersions
- Unbounded auto walks (must pass path-to or Finding package filter)

## When to use this skill vs others

| Ask | Use |
|-----|-----|
| Map AI-SAST entry handlers onto CG nodes / optional path | **This skill** |
| Symbol A → library B on decoded CG only | [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) |
| Finding REACHABLE_FUNCTION vs `oss` callpaths | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |
| Browse / probe vector stores | `endor-vector-query` |

## Prechecks (hard fail)

| Gate id | Requirement |
|---------|-------------|
| `precheck.repository_version_main_aisast` | ≥1 MAIN `RepositoryVersion` with `aisast_status` containing SUCCESS |
| `precheck.function_summary_index` | Tenant-root store `meta.name==function_summary` indexed for project repo |
| `precheck.call_graph_main_pv` | MAIN PackageVersion with `call_graph_available` and successful `CallGraphData.decode` |

## Ordering

1. Credentials — `uv run --env-file .env` (or equivalent).
2. Run bridge CLI (writes JSON under tasks activity dir by default):

```bash
uv run --env-file .env endor-aisast-callgraph \
  --tenant "<tenant>" \
  --namespace "<namespace>" \
  --project "<project-uuid-or-name>"
```

3. Optional **safe** walk from matched seeds to a dependency / sink:

```bash
# Explicit package/symbol patterns (preferred when known)
uv run --env-file .env endor-aisast-callgraph \
  --tenant "<tenant>" \
  --namespace "<namespace>" \
  --project "<project-uuid-or-name>" \
  --path-to "jsonwebtoken" \
  --path-to "sign" \
  --max-depth 8

# Or derive path-to from a MAIN vulnerability Finding (GHSA filters Findings only)
uv run --env-file .env endor-aisast-callgraph \
  --tenant "<tenant>" \
  --namespace "<namespace>" \
  --project "<project-uuid-or-name>" \
  --vuln "GHSA-c7hr-j4mj-j2w6" \
  --path-to-symbol "sign" \
  --max-depth 8
```

4. Library: `endorlabs.workflows.aisast_callgraph.run_aisast_callgraph_bridge`,
   `resolve_vuln_walk_targets`.

## Safe CVE / Finding walk

| Step | Rule |
|------|------|
| 1 | Prechecks pass (MAIN AI-SAST + index + MAIN CG) |
| 2 | Match seeds on `file_path`/`fqn` — never `rest_path` as URI |
| 3 | Resolve Finding → **package token** (`npm://pkg@ver` → `pkg`); GHSA/CVE filter Findings only |
| 4 | Confirm target token exists in callables; skip if not |
| 5 | BFS with `--max-depth` ≤ 12, `--max-paths` ≤ 20; skip source fanout > 40 |
| 6 | Treat path as structural evidence only — hand off Finding reachability to **endor-reachability-provenance** |

## Field join (examples)

| AI-SAST seed | Call Graph |
|--------------|------------|
| `file_path`, `fqn`, `function_info.is_entry_point`, `function_info.rest_path` (metadata only) | `method_id`, `uri`, edge `source_uri`→`target_uri` |
| Patterns derived from path stem / parent folder / FQN tail | Matched via URI substring AND (`resolve_method_ids_by_patterns`) |

`rest_path` is **not** a CG field — use it for human context; patterns come from `file_path` + `fqn`.

## Outputs

- Default: `.endorlabs/tasks/<slug>-<YYYY-MM-DD>/aisast-callgraph/bridge.json`
- Override: `--out <path>`
- Payload: `precheck`, `seeds`, `matches`, optional `vuln_targets`,
  `path_to_resolved`, `paths`, `cg_path_is_not_finding_reachability`,
  `status` / `errors` / `warnings`

## Related skills

| Skill | When |
|-------|------|
| [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) | Pure CG fetch/search after seeds are known |
| [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) | Finding + `oss` stitch |
| [endor-config-presence](../endor-config-presence/SKILL.md) | Broader onboarding presence (includes AI-SAST probes) |
| [endor-project-retrieval-bundle](../endor-project-retrieval-bundle/SKILL.md) | Full project bundle / CG export |
