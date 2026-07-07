---
name: endor-reachability-provenance
description: Investigates reachability provenance mismatches in vulnerability findings by comparing dependency reachability, function reachability, and vulnerability metadata in the oss namespace. Use when finding tags or summary text appear contradictory (for example reachable dependency with unreachable function), when validating affected_callpath_uris attribution, or when analyzing CVE/GHSA alias consistency.
disable-model-invocation: true
endorlabs:
  catalog:
    workflow_id: reachability-context
    cli: endor-reachability-context
    module: endorlabs.workflows.reachability.cli
    default_output: .endorlabs-context/workspace/projects/<uuid>/reachability_context.json
    agent_visible: true
---

# Reachability Provenance

## Purpose

Use this skill to triage findings where reachability signals conflict, especially:

- `REACHABLE_DEPENDENCY` with `UNREACHABLE_FUNCTION`
- summary text saying no vulnerable function is reachable despite suspicious callgraph evidence
- disagreement between CVE and GHSA vulnerability records

## What "oss namespace" is used for

**API path rule:** List and resolve OSS-plane resources under the literal namespace **`oss`**. Do not use `<tenant>.oss`, `<customer>.oss`, or a child namespace under the customer root; `scope="oss"` on the client separates this plane from customer namespace paths.

Use the `oss` namespace as the canonical vulnerability provenance source for:

- vulnerability records returned by query/evaluation
- `affected` entries and version ranges
- `affected_callpath_uris` and `affected_filepaths`
- alias consistency checks across CVE/GHSA IDs
- source attribution fields (for example `SOURCE_OSV`, `SOURCE_ENDOR`)

Do not infer function-level provenance from advisory prose alone when structured `affected_callpath_uris` are available in `oss`.

## Where call graphs are stored (customer vs `oss`)

Reachability triage often mixes two graph planes:

- **Customer tenant graph (project package version):**
  - `CallGraphData` is stored under the customer namespace and is effectively keyed by the importing `PackageVersion` (`meta.parent_uuid == <customer_pv_uuid>`).
  - This graph captures app-side and resolved external-call edges as observed for that project scan.
- **`oss` tenant graph (dependency package version):**
  - For third-party packages, `DependencyMetadata.spec.dependency_data.package_version_uuid` can point to an `oss` package-version UUID.
  - That `oss` package version may have its own `CallGraphData` object(s), independently retrievable in `oss`.
- **Finding metadata bridge:**
  - `Finding.spec.target_uuid` is often a `DependencyMetadata` UUID (customer namespace), not a package-version UUID.
  - `Finding.spec.finding_metadata.vulnerability` commonly embeds vulnerability context sourced from `oss` (including `affected_callpath_uris`).

Practical implication: a finding can be `REACHABLE_FUNCTION` even when a direct path is hard to prove from only the customer `CallGraphData`; the path evidence can be a stitched result across customer graph + `oss` vulnerability/function metadata.

## Workflow

0. Build unified context artifact (default path)
   - Run `uv run endor-reachability-context --tenant <tenant> --namespace <namespace> --finding-uuid <finding_uuid>` (default output: `workspace/projects/<finding-uuid>/reachability_context.json`).
   - Use `--pv-uuid` for direct PV analysis.
   - Treat `reachability_context.json` as the canonical triage bundle (customer graph plane, `oss` graph plane, stitching summary, warnings). `--max-pages` defaults to **0 (unlimited)**; check `list_bounds` and `warnings` when call-graph lists may be capped.
   - Bundle requirement (deterministic): include decoded call graphs from both planes:
     - customer/app side: `app_call_graph_decoded_summary.json`, `app_call_graph_decoded_callables.json`, `app_call_graph_decoded_edges.json`
     - `oss` side: `oss_call_graph_decoded_summary.json`, `oss_call_graph_decoded_callables.json`, `oss_call_graph_decoded_edges.json`

1. Gather finding evidence
   - Record finding UUID, tags, summary, `target_dependency_package_name`, `extra_key`, and `call_graph_analysis_type`.
   - Record whether `reachable_paths` is present.

2. Gather vulnerability provenance from `oss`
   - Fetch vulnerability objects by aliases (for example CVE and GHSA names) in `oss`.
   - For each relevant affected package entry, extract:
     - package identity + ecosystem
     - `affected_callpath_uris`
     - `affected_filepaths`
     - ranges (introduced/fixed/last_affected)
     - source field (`SOURCE_*`)

3. Compare strict function map vs graph evidence
   - Strict check: vulnerable function reachability should be determined from `affected_callpath_uris`.
   - Practical-risk check: inspect whether risky API surface in the same package is reachable even when strict vulnerable callpaths are not matched.
   - Graph-plane check: test customer graph and `oss` graph separately, then test stitched reachability (`customer internal -> shared dependency entrypoint -> oss vulnerable function`).
   - Edge-list requirement (deterministic): when triaging reachability markers, list relevant edges from the source function to candidate target symbols from decoded edge files.
   - Overloaded-symbol scaffold (deterministic): if the same symbol name appears across multiple target edges from the same source, include:
     - `possible_symbol_collision: true`
     - `collision_symbol: <symbol>`

### Control-case method (reachable vs unresolved)

When validating tooling behavior, use one known reachable control and one unresolved case from the same project/tenant:

- **Reachable control (example pattern):** a finding where customer-tenant path plus `oss` callpath metadata agrees (for example Tomcat TOCTOU-style chain with explicit affected functions).
- **Unresolved comparison (example pattern):** a finding where customer graph reaches dependency API surface but cannot statically reach the exact vulnerable methods in `affected_callpath_uris` (possible CG coverage/normalization/runtime-dispatch limits).

Record both outcomes explicitly so the triage output distinguishes:

- data availability issue,
- URI/signature matching issue,
- or true function-level non-reachability.

4. Classify mismatch type
   - **Provenance fragmentation**: aliases disagree or one alias lacks structured function mapping.
   - **Signature normalization mismatch**: semantically equivalent functions fail strict URI matching.
   - **True unreachable function**: dependency reachable, but no strict or equivalent function evidence.
   - **Likely reachable function**: strict or equivalent callpath evidence exists.

5. Produce normalized verdict
   - Distinguish:
     - dependency-level reachability conclusion
     - strict function-level reachability conclusion
     - practical exploitability signal
   - State confidence and likely owner:
     - vuln metadata curation
     - function signature normalization/matching
     - callgraph coverage limitations

## Output Template

Use this structure in the final triage result:

```markdown
## Reachability Provenance Result

- Finding: <finding-id>
- Target dependency: <package@version>
- Call graph analysis type: <full|precomputed|unspecified>

- Dependency reachability: <reachable|unreachable|unknown>
- Function reachability (strict): <reachable|unreachable|unknown>
- Practical risk signal: <present|not present>

- OSS vulnerability provenance:
  - Alias records checked: <list>
  - Structured function map consistency: <consistent|fragmented|missing>
  - Primary source used for function attribution: <SOURCE_*>

- Likely disconnect:
  - <one sentence>

- Recommended next action:
  - <normalization/curation/coverage action>
```

When overloaded edges are present for a symbol, append this deterministic scaffold:

```yaml
overloaded_edge_check:
  source_function: <fully-qualified-source-signature>
  possible_symbol_collision: true
  collision_symbol: <symbol-name>
  relevant_edges:
    - <source> -> <target-1>
    - <source> -> <target-2>
```

## Guardrails

- Do not hardcode a single CVE-specific heuristic.
- Do not treat advisory text as equivalent to structured callpath mapping.
- Prefer structured `affected_callpath_uris` from `oss` for strict conclusions.
- If strict and practical signals diverge, report both explicitly.
- Keep all examples and analysis tenant-neutral and customer-neutral.

## Related skills

| Need | Skill |
| ---- | ----- |
| Finding UUID, project namespace, branch filters | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| Tenant-wide PRF approximation + PV resolution errors | [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) |
| Per-project call graph path search | [endor-fetch-and-search-call-graph](../endor-fetch-and-search-call-graph/SKILL.md) |
| Fixed vs present, dependency graph, SBOM | [endor-dependency-finding-provenance](../endor-dependency-finding-provenance/SKILL.md) |
| Scan aggregate metrics regressed | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |

## Additional Resources

- For sample triage outcomes, see [examples.md](examples.md)
