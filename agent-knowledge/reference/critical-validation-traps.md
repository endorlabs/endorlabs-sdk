# Critical validation traps

Read **`rules/`** (Tier 1 bootstrap) before project-scoped RCA. When behavior
looks wrong, **triangulate** SDK vs `endorctl` vs `contracts/` — skill
**endor-troubleshoot-sdk** ([`validation-reference.md`](../skills/endor-troubleshoot-sdk/validation-reference.md)).

Stable trap ids (for AGENTS.md subset drift checks) are the `##` headings below.

## ambiguous-project-url

`Project.search_by_name(..., traverse=True, max_pages=…)` returns bounded
candidates — pick the row for the intended namespace, narrow `namespace=`, or
use project UUID with `get()`.

## project-scoped-list-namespace

With `Client(tenant=<estate_root>)` and default `traverse=False`, lists hit only
that path segment—not child namespaces where projects live. Resolve `Project`
first, then pass **`namespace=project.namespace`** on `Finding`, `ScanResult`,
`PackageVersion`, `DependencyMetadata`, … Empty rows often mean wrong namespace,
not missing data. Prefer `Finding.list_by_project` / `ScanResult.list_by_project`
when available.

## finding-branch-refs

`spec.source_code_version.ref` may be a short branch label, not
`refs/heads/main`. List findings without a branch filter first; narrow after
inspecting stored refs. `RepositoryVersion.list` can help enumerate refs.

## tenant-wide-scan-cost

`fetch_scan_results --all-projects` is O(projects × scans). Prefer
`--project-name` / `--project-uuid` for interactive RCA.

## list-masks-return-dict

Non-empty `mask=` on `.list()` / `search_by_*` returns `dict` rows, not Pydantic
models. See [contracts/list-parameters.md](../contracts/list-parameters.md).

## dependency-metadata-tenant-plane

List/group uses the **customer tenant namespace**, not the literal `oss` plane.
Field `spec.dependency_data.namespace == "oss"` is data semantics only.

## workflow-composition

Extend workflow JSON/manifests before re-listing the API; escalate CLI → library
→ `Client` → session script (see `rules/endor-workflow-composition.md`).

## portable-examples

Use placeholders in docs, skills, **unit fixtures**, and CLI/docstring examples;
never commit customer estate identifiers (`rules/endor-portable-examples.md`).

## query-malware-vulnerability-create-only

`QueryMalware` / `QueryVulnerability` are create-only catalog facades
(`scope=oss`). There is no `.list()` — use `.create(...)`. Do not import
`endorlabs.query` for these kinds; that module is the graph-join `client.Query`
plane. Hits often appear under `response.list.objects`.

## tenant-malware-exposure

Prefer `MalwareExposure` / `MalwareExposureQuery` (customer namespace) over
`Malware.list` on `oss` for blast-radius asks. Use `QueryMalware` only for
coordinate identity on the catalog plane.

## pagination-completeness-capped

`ResourcePage.completeness` is `complete` only when the server returned no next
cursor. Client `max_pages` / `max_items` caps yield `capped`; deadline/cancel
yield `unknown`. An empty `items` list with `completeness != "complete"` is
**not** proof of absence — use `list_pages` / `list_pages_by_project` /
`list_pages_for_context` when hosts must distinguish stop reasons. Flat
`list()` materializes rows without completeness metadata.

## route-context-edge-required

`list_for_context` / `list_pages_for_context` apply only to kinds with a
route-contract `list_by_context_partition` edge (Finding, PackageVersion,
DependencyMetadata, …). Calling them on `ScanResult` / `Project` raises
`RouteNotApplicableError`. Prefer
`endorlabs.describe_resource(attr).route_methods` (offline) or
`client.<Kind>.describe()` before assuming mixin methods exist.

## scan-dependency-receipt-unavailable

`read_scan_dependency_receipt(...)` returns a typed receipt with
`status="unavailable"` until a platform scan-bound digest read exists. Do
**not** invent digests or substitute Artifact / PackageVersionSourceMetadata
checksums as scan evidence.
